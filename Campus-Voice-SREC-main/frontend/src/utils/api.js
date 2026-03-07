// Use the Vite proxy for local dev so all /api requests go through localhost:8000
// In production set VITE_API_URL to the production API URL (with or without /api suffix)
const _rawBase = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
const API_BASE_URL = _rawBase
  ? (_rawBase.endsWith('/api') ? _rawBase : `${_rawBase}/api`)
  : '/api';

/**
 * Decodes a JWT token manually to extract the payload.
 * Useful for getting the role and expiration without an external library.
 */
export const decodeToken = (token) => {
    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(
            window.atob(base64)
                .split('')
                .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
                .join('')
        );
        return JSON.parse(jsonPayload);
    } catch (error) {
        console.error('Failed to decode token:', error);
        return null;
    }
};

// ==================== TOKEN STORAGE ====================
// Access token: sessionStorage (cleared when tab/browser closes)
// Refresh token: localStorage  (persists across sessions)

export const tokenStorage = {
    getAccessToken: () => sessionStorage.getItem('access_token') || localStorage.getItem('token'),
    setAccessToken: (t) => { sessionStorage.setItem('access_token', t); },
    getRefreshToken: () => localStorage.getItem('refresh_token'),
    setRefreshToken: (t) => { localStorage.setItem('refresh_token', t); },
    clearAll: () => {
        sessionStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        // Legacy key cleanup
        localStorage.removeItem('token');
        localStorage.removeItem('user');
    },
};

// ==================== TOKEN REFRESH LOGIC ====================
// Single in-flight refresh promise — concurrent 401s queue behind it.
let _refreshPromise = null;

const _clearSessionAndRedirect = () => {
    tokenStorage.clearAll();
    window.location.href = '/login';
};

const _attemptRefresh = async () => {
    if (_refreshPromise) return _refreshPromise;

    _refreshPromise = (async () => {
        const refreshToken = tokenStorage.getRefreshToken();
        if (!refreshToken) {
            _clearSessionAndRedirect();
            return null;
        }

        try {
            const resp = await fetch(`${API_BASE_URL}/auth/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: refreshToken }),
            });

            if (!resp.ok) {
                console.warn('Refresh token rejected by server. Logging out.');
                _clearSessionAndRedirect();
                return null;
            }

            const data = await resp.json();
            const newAccessToken = data.access_token;
            tokenStorage.setAccessToken(newAccessToken);
            return newAccessToken;
        } catch (err) {
            console.error('Token refresh network error:', err);
            _clearSessionAndRedirect();
            return null;
        } finally {
            _refreshPromise = null;
        }
    })();

    return _refreshPromise;
};

// ==================== PROACTIVE TOKEN VALIDATION ====================
// Check expiry BEFORE firing — stops the burst of 401s on page load when all
// components mount simultaneously with a stale access token in sessionStorage.

const _isTokenExpired = (token) => {
    if (!token) return true;
    try {
        const payload = decodeToken(token);
        if (!payload?.exp) return false;
        // Expire 10s early to account for clock skew / network latency
        return Date.now() / 1000 > payload.exp - 10;
    } catch {
        return true;
    }
};

const _getValidToken = async () => {
    const token = tokenStorage.getAccessToken();
    // No access token at all — only try refresh if we have a refresh token.
    // If there's neither, the user is not logged in; return null so the request
    // fires without auth (public endpoints like /login handle this correctly).
    if (!token) {
        return tokenStorage.getRefreshToken() ? await _attemptRefresh() : null;
    }
    if (_isTokenExpired(token)) {
        return await _attemptRefresh();
    }
    return token;
};

// ==================== CORE FETCH WRAPPER ====================

/**
 * A wrapper around fetch that handles:
 * 1. Proactively refreshing the access token if expired before firing.
 * 2. Attaching the Bearer (access) token.
 * 3. Parsing JSON responses.
 * 4. On 401: automatically attempts one token refresh then retries.
 * 5. On refresh failure: clears storage and redirects to /login.
 */
export const api = async (endpoint, options = {}, _isRetry = false) => {
    // On retry, token was just refreshed — read it directly to avoid double refresh.
    const token = _isRetry
        ? tokenStorage.getAccessToken()
        : await _getValidToken();

    const headers = {
        ...options.headers,
    };

    // Only set Content-Type to application/json if we're NOT sending FormData
    if (!(options.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
    }

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const config = {
        ...options,
        headers,
    };

    // Ensure endpoint starts with / for consistency
    const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = `${API_BASE_URL}${path}`;

    try {
        const response = await fetch(url, config);

        // Handle 204 No Content
        if (response.status === 204) return null;

        // Handle non-JSON responses (like binary image data)
        const contentType = response.headers.get('content-type') || '';
        if (contentType.startsWith('image/')) {
            if (!response.ok) {
                throw new Error(`Image request failed with status ${response.status}`);
            }
            return response; // Return raw response for blob handling
        }

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            console.error('API Error Response:', { status: response.status, data });

            if (response.status === 401 && !_isRetry) {
                // Access token expired — try to refresh once
                const newToken = await _attemptRefresh();
                if (newToken) {
                    // Retry the original request with the new token
                    return api(endpoint, options, true);
                }
                // _attemptRefresh already redirected to login
                return;
            }

            if (response.status === 401 && _isRetry) {
                // Even after refresh, still 401 — give up
                console.warn('Still 401 after token refresh. Logging out.');
                _clearSessionAndRedirect();
                return;
            }

            // Surface the most useful error message from backend
            const message = data.error || data.detail || data.message || `Request failed with status ${response.status}`;
            const err = new Error(message);
            err.status = response.status;
            err.data = data;
            throw err;
        }

        return data;
    } catch (error) {
        // Re-throw errors that already have our shape
        if (error.status) throw error;
        console.error('API Network/Code Error:', error);
        throw error;
    }
};

/**
 * Fetch a binary resource (e.g. image) and return a blob URL.
 * Authorization header is attached automatically.
 */
export const fetchBlobUrl = async (endpoint, options = {}) => {
    const token = tokenStorage.getAccessToken();
    const headers = { ...options.headers };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = `${API_BASE_URL}${path}`;

    const response = await fetch(url, { ...options, headers });
    if (!response.ok) {
        throw new Error(`Failed to fetch binary resource: ${response.status}`);
    }
    const blob = await response.blob();
    return URL.createObjectURL(blob);
};

export default api;
