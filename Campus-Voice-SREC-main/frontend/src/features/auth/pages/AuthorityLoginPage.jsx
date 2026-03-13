import React from 'react';
import { Navigate } from 'react-router-dom';

export default function AuthorityLoginPage() {
  return <Navigate to="/login?role=authority" replace />;
}
