import React, { createContext, useState, useEffect, useContext } from 'react';
import authService from '../services/auth.service';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initializeApp = async () => {
      try {
        // Wake up backend (Render free tier may be sleeping)
        const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://campusvoice-api-h528.onrender.com/api';
        const healthUrl = API_BASE_URL.replace('/api', '') + '/health';

        // Ping backend without waiting for response (fire and forget)
        fetch(healthUrl).catch(() => {
          // Ignore errors - backend will wake up in background
        });

        // Check if user is logged in
        const user = authService.getCurrentUser();
        if (user) {
          setCurrentUser(user);
        }
      } catch (error) {
        console.error('Initialization error:', error);
      } finally {
        // Small delay to ensure backend has time to wake up
        setTimeout(() => {
          setLoading(false);
        }, 1000);
      }
    };

    initializeApp();
  }, []);

  const loginStudent = async (email, password) => {
    const data = await authService.loginStudent(email, password);
    setCurrentUser(data); // data is the user object with role merged
    // Trigger push subscription now that user is logged in
    if (typeof window._cvSetupPush === 'function') window._cvSetupPush();
    return data;
  };

  const loginAuthority = async (email, password) => {
    const data = await authService.loginAuthority(email, password);
    setCurrentUser(data);
    return data;
  };

  const signup = async (userData) => {
    return await authService.signup(userData);
  };

  const logout = () => {
    authService.logout();
    setCurrentUser(null);
  };

  const value = {
    user: currentUser,
    loginStudent,
    loginAuthority,
    signup,
    logout,
    loading
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  return useContext(AuthContext);
};
