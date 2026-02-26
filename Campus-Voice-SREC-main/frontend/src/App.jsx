import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { NotificationProvider } from './context/NotificationContext';
import LoginPage from './features/auth/pages/LoginPage';
import AuthorityLoginPage from './features/auth/pages/AuthorityLoginPage';
import StudentHome from './features/complaints/pages/StudentHome';
import ComplaintDetails from './features/complaints/pages/ComplaintDetails';
// Admin Imports
import AdminLayout from './features/admin/layout/AdminLayout';
import AdminDashboard from './features/admin/pages/AdminDashboard';
import AdminAllComplaints from './features/admin/pages/AdminAllComplaints';
import AdminAuthorities from './features/admin/pages/AdminAuthorities';
import AdminEscalations from './features/admin/pages/AdminEscalations';
import AdminDepartments from './features/admin/pages/AdminDepartments';
import AdminDepartmentsList from './features/admin/pages/AdminDepartmentsList';
import AdminDepartmentDetail from './features/admin/pages/AdminDepartmentDetail';
import AdminNotifications from './features/admin/pages/AdminNotifications';

import AuthorityDashboard from './features/admin/pages/AuthorityDashboard';
import AuthorityNotifications from './features/admin/pages/AuthorityNotifications';
import AuthorityProfile from './features/admin/pages/AuthorityProfile';
import AuthorityNotices from './features/admin/pages/AuthorityNotices';
import InstallPrompt from './components/InstallPrompt';
import SignupPage from './features/auth/pages/SignupPage';
import Onboarding from './features/auth/pages/Onboarding';
import Profile from './features/profile/pages/Profile';
import Posts from './features/complaints/pages/Posts';
import Notifications from './features/complaints/pages/Notifications';
import NoticeFeed from './features/complaints/pages/NoticeFeed';

function ProtectedRoute({ children, allow, redirectTo = "/login" }) {
  const { user } = useAuth();
  if (!user) return <Navigate to={redirectTo} replace />;

  const userRole = user.role.toLowerCase();
  const allowedRoles = allow ? allow.map(r => r.toLowerCase()) : [];

  if (allow && allow.length && !allowedRoles.includes(userRole)) {
    if (userRole === 'admin') return <Navigate to="/admin" replace />;
    if (userRole === 'authority') return <Navigate to="/authority-dashboard" replace />;
    return <Navigate to="/home" replace />;
  }
  return children;
}

function DashboardRedirect() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;

  const role = user.role.toLowerCase();
  if (role === 'admin') return <Navigate to="/admin" replace />;
  if (role === 'authority') return <Navigate to="/authority-dashboard" replace />;

  const last = localStorage.getItem('cv_last_tab');
  if (last && last !== '/dashboard' && last !== '/') return <Navigate to={last} replace />;
  return <Navigate to="/home" replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <NotificationProvider>
      <InstallPrompt />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/authority-login" element={<Navigate to="/login?role=authority" replace />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/dashboard" element={<DashboardRedirect />} />
        <Route path="/" element={<DashboardRedirect />} />

        {/* Student Routes */}
        <Route
          path="/home"
          element={
            <ProtectedRoute allow={['Student', 'Admin']}>
              <StudentHome />
            </ProtectedRoute>
          }
        />
        <Route
          path="/complaint/:id"
          element={
            <ProtectedRoute allow={['Student', 'Authority', 'Admin']}>
              <ComplaintDetails />
            </ProtectedRoute>
          }
        />
        <Route
          path="/posts"
          element={
            <ProtectedRoute allow={['Student', 'Admin']}>
              <Posts />
            </ProtectedRoute>
          }
        />
        <Route
          path="/notifications"
          element={
            <ProtectedRoute allow={['Student', 'Admin']}>
              <Notifications />
            </ProtectedRoute>
          }
        />
        <Route
          path="/notices"
          element={
            <ProtectedRoute allow={['Student', 'Admin']}>
              <NoticeFeed />
            </ProtectedRoute>
          }
        />
        <Route
          path="/profile"
          element={
            <ProtectedRoute allow={['Student', 'Admin']}>
              <Profile />
            </ProtectedRoute>
          }
        />

        {/* Admin Routes - Nested under AdminLayout */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute allow={['Admin']}>
              <AdminLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<AdminDashboard />} />
          <Route path="complaints" element={<AdminAllComplaints />} />
          <Route path="authorities" element={<AdminAuthorities />} />
          <Route path="escalations" element={<AdminEscalations />} />
          <Route path="departments" element={<AdminDepartments />} />
          <Route path="departments/list" element={<AdminDepartmentsList />} />
          <Route path="departments/:deptCode" element={<AdminDepartmentDetail />} />
          <Route path="notifications" element={<AdminNotifications />} />
          <Route path="profile" element={<AuthorityProfile noLayout={true} />} />
        </Route>

        {/* Authority Routes */}
        <Route
          path="/authority-dashboard"
          element={
            <ProtectedRoute allow={['Authority', 'Admin']} redirectTo="/authority-login">
              <AuthorityDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/authority-notifications"
          element={
            <ProtectedRoute allow={['Authority', 'Admin']} redirectTo="/authority-login">
              <AuthorityNotifications />
            </ProtectedRoute>
          }
        />
        <Route
          path="/authority-profile"
          element={
            <ProtectedRoute allow={['Authority', 'Admin']} redirectTo="/authority-login">
              <AuthorityProfile />
            </ProtectedRoute>
          }
        />
        <Route
          path="/authority-notices"
          element={
            <ProtectedRoute allow={['Authority', 'Admin']} redirectTo="/authority-login">
              <AuthorityNotices />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
      </NotificationProvider>
    </AuthProvider>
  );
}
