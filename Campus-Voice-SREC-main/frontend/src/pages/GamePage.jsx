import React from 'react';
import { useNavigate } from 'react-router-dom';
import OfflineGame from '../components/OfflineGame';

export default function GamePage() {
  const navigate = useNavigate();
  return <OfflineGame onClose={() => navigate(-1)} />;
}
