import { api, decodeToken, tokenStorage } from '../utils/api';

const loginStudent = async (email_or_roll_no, password) => {
    const data = await api('/students/login', {
        method: 'POST',
        body: JSON.stringify({ email_or_roll_no, password }),
    });
    return handleLoginResponse(data);
};

const loginAuthority = async (email, password) => {
    const data = await api('/authorities/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
    });
    return handleLoginResponse(data);
};

const handleLoginResponse = (data) => {
    // Backend returns `token` (access token) and optionally `refresh_token`
    const accessToken = data.token || data.access_token;
    if (!accessToken) return data;

    // Store access token in sessionStorage, refresh token in localStorage
    tokenStorage.setAccessToken(accessToken);
    if (data.refresh_token) {
        tokenStorage.setRefreshToken(data.refresh_token);
    }

    // Decode token to get the authoritative role
    const decoded = decodeToken(accessToken);

    const userWithRole = {
        ...data,
        role: decoded?.role,
    };

    // If the backend returns a nested 'user' object, flatten it
    if (data.user) {
        Object.assign(userWithRole, data.user);
    }

    // Persist user profile (non-token fields) for getCurrentUser()
    localStorage.setItem('user', JSON.stringify(userWithRole));

    return userWithRole;
};

const signup = async (userData) => {
    const data = await api('/students/register', {
        method: 'POST',
        body: JSON.stringify(userData),
    });
    // Registration also returns tokens — store them
    return handleLoginResponse(data);
};

const logout = () => {
    tokenStorage.clearAll();
    navigator.clearAppBadge?.();
    window.location.href = '/login';
};

const getCurrentUser = () => {
    const userStr = localStorage.getItem('user');
    // Prefer sessionStorage access token; fall back to legacy localStorage key
    const accessToken = tokenStorage.getAccessToken();
    const refreshToken = tokenStorage.getRefreshToken();

    // A session is considered valid if we have either an unexpired access token
    // OR a refresh token (the interceptor will silently refresh on next API call)
    if (!userStr) return null;

    try {
        const user = JSON.parse(userStr);
        if (!user || typeof user !== 'object') return null;

        if (accessToken) {
            const decoded = decodeToken(accessToken);
            // If access token exists and is not expired, use it
            if (decoded?.role && decoded.exp * 1000 > Date.now()) {
                return user;
            }
        }

        // Access token missing or expired — check if we have a valid refresh token.
        // If yes, return the user object anyway; the api() interceptor will
        // transparently refresh the access token on the next API call.
        if (refreshToken) {
            const decodedRefresh = decodeToken(refreshToken);
            if (decodedRefresh && decodedRefresh.exp * 1000 > Date.now()) {
                return user;
            }
        }

        // Both tokens expired or missing — clear and treat as logged-out
        tokenStorage.clearAll();
        return null;
    } catch (e) {
        return null;
    }
};

const authService = {
    loginStudent,
    loginAuthority,
    signup,
    logout,
    getCurrentUser,
};

export default authService;
