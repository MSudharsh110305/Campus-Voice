import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, User, Megaphone } from 'lucide-react';
import { useAuth } from '../../../context/AuthContext';

const AuthoritySidebar = ({ className = '' }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();

  const menuItems = [
    { icon: LayoutDashboard, label: 'Dashboard', path: '/authority-dashboard' },
    { icon: Megaphone, label: 'Notices', path: '/authority-notices' },
    { icon: User, label: 'Profile', path: '/authority-profile' },
  ];

  return (
    <div className={`w-64 bg-white min-h-screen border-r border-gray-100 flex flex-col ${className}`}>
      <div className="p-6 border-b border-gray-100">
        <h2 className="text-xl font-bold text-srec-primary tracking-tight">CampusVoice</h2>
        <p className="text-xs text-srec-primaryHover font-medium mt-1 uppercase tracking-wider">Authority Panel</p>
      </div>

      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {menuItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <button
              key={item.label}
              onClick={() => navigate(item.path)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group ${isActive
                ? 'bg-srec-primary/[0.08] text-srec-primary font-semibold'
                : 'text-gray-500 hover:bg-gray-50 hover:text-srec-primary'
                }`}
            >
              <item.icon
                size={20}
                className={`transition-colors duration-200 ${isActive ? 'text-srec-primary' : 'text-gray-400 group-hover:text-srec-primary'
                  }`}
              />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
};

export default AuthoritySidebar;
