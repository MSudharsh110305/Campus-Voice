# 🔐 CampusVoice Frontend Authentication Guide

## Tamil Translation / தமிழ் விளக்கம்

> **Frontend Dev-க்கு:**
> "Andha token logic epdi work aaguthu nu therla... Oru time login aaguthu next time failed to fetch nu varuthu"
>
> **Answer:**
> Token-ah **localStorage/sessionStorage-la save pannanum**. Aprom **every request-kum** Authorization header-la send pannanum. Indha guide-la **step-by-step solren**.

---

## 🎯 Quick Fix Checklist

If you're getting "failed to fetch" errors:

- [ ] **CORS fixed?** Push the latest code (we just added your LAN IP)
- [ ] **Token stored?** Check `localStorage.getItem('token')` in console
- [ ] **Token sent?** Check Network tab → Request Headers → `Authorization: Bearer <token>`
- [ ] **Token expired?** Tokens expire after **7 days** (check login date)
- [ ] **Correct header format?** Must be `Authorization: Bearer <token>` (note the space)

---

## 📚 How JWT Authentication Works

### 1. **Login Flow** (Get Token)

**Endpoint:** `POST /api/students/login` or `POST /api/authorities/login`

**Request:**
```json
{
  "email_or_roll_no": "arjun.test@srec.ac.in",
  "password": "Test@1234"
}
```

**Response (Success - 200):**
```json
{
  "success": true,
  "message": "Login successful",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "roll_no": "24CS101",
    "name": "Arjun Kumar",
    "email": "arjun.test@srec.ac.in",
    "department_code": "CSE",
    "gender": "Male",
    "stay_type": "Hostel",
    "year": 2
  }
}
```

**Response (Failed - 401):**
```json
{
  "success": false,
  "error": "Invalid credentials"
}
```

---

### 2. **Store Token in Frontend**

**After successful login, IMMEDIATELY save the token:**

```javascript
// React Example
const handleLogin = async (email, password) => {
  try {
    const response = await fetch('https://campusvoice-api-h528.onrender.com/api/students/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email_or_roll_no: email,
        password: password
      })
    });

    const data = await response.json();

    if (response.ok && data.token) {
      // ✅ CRITICAL: Store token
      localStorage.setItem('campusvoice_token', data.token);
      localStorage.setItem('campusvoice_user', JSON.stringify(data.user));

      console.log('✅ Login successful, token saved');
      // Redirect to dashboard
      navigate('/dashboard');
    } else {
      console.error('❌ Login failed:', data.error);
      alert(data.error || 'Login failed');
    }
  } catch (error) {
    console.error('❌ Network error:', error);
    alert('Failed to connect to server. Check your internet connection.');
  }
};
```

---

### 3. **Send Token with Every Protected Request**

**ALL requests to protected endpoints MUST include the Authorization header:**

```javascript
// React Example - Get user profile
const getUserProfile = async () => {
  try {
    // ✅ Get token from storage
    const token = localStorage.getItem('campusvoice_token');

    if (!token) {
      console.error('❌ No token found. User not logged in.');
      navigate('/login');
      return;
    }

    const response = await fetch('https://campusvoice-api-h528.onrender.com/api/students/profile', {
      method: 'GET',
      headers: {
        // ✅ CRITICAL: Include Authorization header
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      }
    });

    if (response.status === 401) {
      console.error('❌ Token expired or invalid');
      localStorage.removeItem('campusvoice_token');
      localStorage.removeItem('campusvoice_user');
      navigate('/login');
      return;
    }

    const data = await response.json();
    console.log('✅ Profile fetched:', data);
    return data;

  } catch (error) {
    console.error('❌ Failed to fetch profile:', error);
  }
};
```

---

### 4. **Create Axios Instance (Recommended)**

**Instead of manually adding headers every time, create a configured Axios instance:**

```javascript
// src/api/axios.js
import axios from 'axios';

const API_BASE_URL = 'https://campusvoice-api-h528.onrender.com/api';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  }
});

// ✅ Add token to every request automatically
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('campusvoice_token');

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    console.log(`🔵 ${config.method.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('❌ Request error:', error);
    return Promise.reject(error);
  }
);

// ✅ Handle token expiration automatically
api.interceptors.response.use(
  (response) => {
    console.log(`✅ ${response.config.method.toUpperCase()} ${response.config.url} - ${response.status}`);
    return response;
  },
  (error) => {
    console.error(`❌ ${error.config?.method?.toUpperCase()} ${error.config?.url} - ${error.response?.status}`);

    // Token expired or invalid
    if (error.response?.status === 401) {
      console.error('❌ Token expired. Redirecting to login...');
      localStorage.removeItem('campusvoice_token');
      localStorage.removeItem('campusvoice_user');
      window.location.href = '/login';
    }

    return Promise.reject(error);
  }
);

export default api;
```

**Now use it in your components:**

```javascript
// src/components/Dashboard.jsx
import api from '../api/axios';

const Dashboard = () => {
  const [profile, setProfile] = useState(null);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        // ✅ Token is automatically included by interceptor
        const response = await api.get('/students/profile');
        setProfile(response.data);
      } catch (error) {
        console.error('Failed to fetch profile:', error);
      }
    };

    fetchProfile();
  }, []);

  // ... rest of component
};
```

---

## 🔍 Token Structure (JWT)

Your token looks like this:
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhcmp1bi50ZXN0QHNyZWMuYWMuaW4iLCJyb2xlIjoiU3R1ZGVudCIsImV4cCI6MTczMzY3MTIwMH0.signature
```

**It has 3 parts separated by dots (.):**

1. **Header**: `eyJhbGci...` (algorithm info)
2. **Payload**: `eyJzdWI...` (user data - email, role, expiration)
3. **Signature**: `signature` (verification)

**Decode the payload at [jwt.io](https://jwt.io) to see:**
```json
{
  "sub": "arjun.test@srec.ac.in",    // User identifier (email)
  "role": "Student",                  // User role
  "exp": 1733671200                   // Expiration timestamp
}
```

---

## ⏰ Token Expiration

**Token Lifetime:** **7 days** (168 hours)

After 7 days, the token expires and you get:

```json
{
  "success": false,
  "error": "Token has expired",
  "error_code": "TOKEN_EXPIRED"
}
```

**Solution:** User must login again to get a new token.

**Check token expiration in code:**

```javascript
const isTokenExpired = (token) => {
  try {
    // Decode JWT payload (middle part)
    const payload = JSON.parse(atob(token.split('.')[1]));
    const exp = payload.exp * 1000; // Convert to milliseconds
    const now = Date.now();

    return now > exp;
  } catch (error) {
    return true; // Invalid token
  }
};

// Usage
const token = localStorage.getItem('campusvoice_token');
if (token && isTokenExpired(token)) {
  console.warn('⚠️ Token expired. Redirecting to login...');
  localStorage.removeItem('campusvoice_token');
  navigate('/login');
}
```

---

## 🚨 Common Errors & Solutions

### 1. **"Failed to fetch"**

**Cause:** CORS issue or network problem

**Solution:**
- ✅ We just fixed CORS (push the latest code)
- Check DevTools → Console for CORS errors
- Ensure backend is running: https://campusvoice-api-h528.onrender.com/health

---

### 2. **401 Unauthorized - "Missing authorization header"**

**Cause:** Token not sent with request

**Error Response:**
```json
{
  "success": false,
  "error": "Missing authorization header",
  "error_code": "MISSING_TOKEN"
}
```

**Solution:**
```javascript
// ❌ WRONG (no Authorization header)
fetch('/api/students/profile', {
  method: 'GET'
})

// ✅ CORRECT
fetch('/api/students/profile', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
```

---

### 3. **401 Unauthorized - "Invalid authorization format"**

**Cause:** Wrong header format

**Error Response:**
```json
{
  "success": false,
  "error": "Invalid authorization format",
  "error_code": "INVALID_TOKEN_FORMAT"
}
```

**Solution:**
```javascript
// ❌ WRONG (missing "Bearer" prefix)
headers: {
  'Authorization': token
}

// ❌ WRONG (no space after "Bearer")
headers: {
  'Authorization': `Bearer${token}`
}

// ✅ CORRECT (note the space after "Bearer")
headers: {
  'Authorization': `Bearer ${token}`
}
```

---

### 4. **401 Unauthorized - "Token has expired"**

**Cause:** Token is older than 7 days

**Error Response:**
```json
{
  "success": false,
  "error": "Token has expired",
  "error_code": "TOKEN_EXPIRED"
}
```

**Solution:**
```javascript
// Redirect to login
if (error.response?.data?.error_code === 'TOKEN_EXPIRED') {
  alert('Your session has expired. Please login again.');
  localStorage.removeItem('campusvoice_token');
  navigate('/login');
}
```

---

### 5. **401 Unauthorized - "Invalid token"**

**Cause:** Token is corrupted or fake

**Error Response:**
```json
{
  "success": false,
  "error": "Invalid token",
  "error_code": "INVALID_TOKEN"
}
```

**Solution:**
```javascript
// Clear storage and redirect to login
localStorage.removeItem('campusvoice_token');
localStorage.removeItem('campusvoice_user');
navigate('/login');
```

---

## 🔧 Debugging Tips

### Check Token in Browser Console

```javascript
// Check if token exists
const token = localStorage.getItem('campusvoice_token');
console.log('Token:', token);

// Decode token to see payload
if (token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    console.log('Token Payload:', payload);
    console.log('User:', payload.sub);
    console.log('Role:', payload.role);
    console.log('Expires:', new Date(payload.exp * 1000));
    console.log('Expired?', Date.now() > payload.exp * 1000);
  } catch (e) {
    console.error('Invalid token format');
  }
}
```

### Check Request Headers in Network Tab

1. Open **DevTools** (F12)
2. Go to **Network** tab
3. Make a request (e.g., fetch profile)
4. Click the request
5. Check **Request Headers** section
6. Look for:
   ```
   Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

---

## 📋 Complete Example (React)

```javascript
// src/App.jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';

function App() {
  const isAuthenticated = () => {
    const token = localStorage.getItem('campusvoice_token');
    if (!token) return false;

    // Check if expired
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return Date.now() < payload.exp * 1000;
    } catch {
      return false;
    }
  };

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/dashboard"
          element={isAuthenticated() ? <Dashboard /> : <Navigate to="/login" />}
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
```

---

## 🔒 Public vs Protected Routes

### Public Routes (No Token Required)

- `POST /api/students/register` - Student registration
- `POST /api/students/login` - Student login
- `POST /api/authorities/login` - Authority login
- `GET /health` - Health check

### Protected Routes (Token Required)

**All other routes need `Authorization: Bearer <token>` header:**

- `GET /api/students/profile` - Get student profile
- `POST /api/complaints/submit` - Submit complaint
- `GET /api/complaints/public-feed` - Get public feed
- `POST /api/complaints/{id}/vote` - Vote on complaint
- `GET /api/authorities/my-complaints` - Authority's complaints
- ... (all other endpoints)

---

## 🎯 Final Checklist for Frontend Dev

- [ ] Store token in localStorage after login
- [ ] Send `Authorization: Bearer <token>` header with every protected request
- [ ] Handle 401 errors by redirecting to login
- [ ] Check token expiration before making requests
- [ ] Clear token on logout
- [ ] Use Axios interceptors for automatic token handling (recommended)
- [ ] CORS origins now include your LAN IP (after you push latest code)

---

## 🚀 Testing Your Integration

**1. Test Health Endpoint (No Token):**
```javascript
fetch('https://campusvoice-api-h528.onrender.com/health')
  .then(r => r.json())
  .then(d => console.log('✅ Backend is alive:', d))
  .catch(e => console.error('❌ Backend is down:', e));
```

**2. Test Login (Get Token):**
```javascript
fetch('https://campusvoice-api-h528.onrender.com/api/students/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email_or_roll_no: 'arjun.test@srec.ac.in',
    password: 'Test@1234'
  })
})
.then(r => r.json())
.then(d => {
  console.log('✅ Login response:', d);
  if (d.token) {
    localStorage.setItem('campusvoice_token', d.token);
    console.log('✅ Token saved');
  }
})
.catch(e => console.error('❌ Login failed:', e));
```

**3. Test Protected Endpoint (With Token):**
```javascript
const token = localStorage.getItem('campusvoice_token');
fetch('https://campusvoice-api-h528.onrender.com/api/students/profile', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
})
.then(r => r.json())
.then(d => console.log('✅ Profile:', d))
.catch(e => console.error('❌ Profile fetch failed:', e));
```

---

## 🎉 Summary (Tamil)

**Token epdi use pannurathu:**

1. **Login pannu** → Token varum
2. **Token-ah localStorage-la save pannu**
3. **Every request-kum Authorization header-la token send pannu:**
   ```javascript
   headers: {
     'Authorization': `Bearer ${token}`
   }
   ```
4. **401 error vandhaa** → Token expired/invalid → Logout pannu, login page-ku redirect pannu

**"Failed to fetch" problem-ku:**
- Backend alive-ah irukka check pannu (health endpoint)
- CORS fixed-ah irukka check pannu (latest code push pannanum)
- Token correct-ah send aagudha check pannu (Network tab)

**Questions-ah irundhaa ping pannu! 🚀**
