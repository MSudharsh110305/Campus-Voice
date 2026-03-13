import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, User, Megaphone, ScrollText, UserCheck, ChevronDown } from 'lucide-react';
import { useAuth } from '../../../context/AuthContext';

const AuthoritySidebar = ({ className = '', onClose }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [communityOpen, setCommunityOpen] = useState(
    location.pathname === '/authority-petitions' ||
    location.pathname === '/authority-representatives'
  );

  const isActive = (path) => location.pathname === path;
  const isCommunityActive = isActive('/authority-petitions') || isActive('/authority-representatives');

  const NavBtn = ({ path, icon: Icon, label }) => {
    const active = isActive(path);
    return (
      <button
        onClick={() => { navigate(path); onClose?.(); }}
        className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all duration-200 group ${
          active ? 'bg-srec-primary/[0.08] text-srec-primary font-semibold' : 'text-gray-500 hover:bg-gray-50 hover:text-srec-primary'
        }`}
      >
        <Icon size={18} className={`transition-colors duration-200 ${active ? 'text-srec-primary' : 'text-gray-400 group-hover:text-srec-primary'}`} />
        <span className="text-sm">{label}</span>
      </button>
    );
  };

  return (
    <div className={`w-64 bg-white h-full min-h-screen border-r border-gray-100 flex flex-col overflow-y-auto ${className}`}>
      <div className="p-6 border-b border-gray-100">
        <h2 className="text-xl font-bold text-srec-primary tracking-tight">CampusVoice</h2>
        <p className="text-xs text-srec-primaryHover font-medium mt-1 uppercase tracking-wider">Authority Panel</p>
      </div>

      <nav className="flex-1 p-4 space-y-0.5 overflow-y-auto">
        <NavBtn path="/authority-dashboard" icon={LayoutDashboard} label="Dashboard" />

        {/* Community accordion */}
        <div>
          <button
            onClick={() => setCommunityOpen(o => !o)}
            className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all duration-200 ${
              isCommunityActive ? 'bg-srec-primary/[0.08] text-srec-primary' : 'text-gray-500 hover:bg-gray-50 hover:text-srec-primary'
            }`}
          >
            <ScrollText size={18} className={isCommunityActive ? 'text-srec-primary' : 'text-gray-400'} />
            <span className={`text-sm flex-1 text-left ${isCommunityActive ? 'font-semibold' : ''}`}>Community</span>
            <ChevronDown size={14} className={`transition-transform duration-200 ${communityOpen ? 'rotate-180' : ''}`} />
          </button>
          {communityOpen && (
            <div className="ml-4 mt-0.5 space-y-0.5 border-l border-gray-100 pl-2">
              <NavBtn path="/authority-petitions" icon={ScrollText} label="Petitions" />
              <NavBtn path="/authority-representatives" icon={UserCheck} label="Representatives" />
            </div>
          )}
        </div>

        <NavBtn path="/authority-notices" icon={Megaphone} label="Notices" />
        <NavBtn path="/authority-profile" icon={User} label="Profile" />
      </nav>
    </div>
  );
};

export default AuthoritySidebar;
