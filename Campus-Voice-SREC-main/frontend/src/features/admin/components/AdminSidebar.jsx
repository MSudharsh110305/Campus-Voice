import React, { useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  FileText,
  Users,
  GraduationCap,
  Building2,
  TriangleAlert,
  UserCog,
  LogOut,
  ShieldCheck,
  ChevronDown,
  ScrollText,
  UserCheck,
  Megaphone,
} from "lucide-react";
import { useAuth } from '../../../context/AuthContext';

export default function AdminSidebar({ className = "", onClose }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [usersOpen, setUsersOpen] = useState(
    location.pathname.startsWith('/admin/students') ||
    location.pathname.startsWith('/admin/authorities')
  );
  const [communityOpen, setCommunityOpen] = useState(
    location.pathname.startsWith('/admin/petitions') ||
    location.pathname.startsWith('/admin/representatives')
  );

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  const initials = user?.name?.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || 'A';

  const isActive = (path, exact = false) =>
    exact ? location.pathname === path : location.pathname.startsWith(path);

  const NavItem = ({ path, icon: Icon, label, exact = false }) => {
    const active = isActive(path, exact);
    return (
      <NavLink to={path} onClick={onClose}>
        <div className={`flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-150 ${
          active
            ? 'bg-srec-primarySoft text-srec-primary border-l-[3px] border-srec-primary pl-2.5 shadow-inner-soft'
            : 'text-srec-textSecondary hover:bg-srec-backgroundAlt hover:text-srec-textPrimary border-l-[3px] border-transparent pl-2.5'
        }`}>
          <Icon size={18} className={active ? 'text-srec-primary' : 'text-srec-textMuted'} strokeWidth={active ? 2.5 : 2} />
          <span className={`text-sm ${active ? 'font-semibold' : 'font-medium'}`}>{label}</span>
        </div>
      </NavLink>
    );
  };

  return (
    <aside className={`w-64 flex-shrink-0 flex flex-col bg-white/80 backdrop-blur-xl border-r border-srec-borderLight shadow-soft ${className}`}>
      {/* Brand header */}
      <div className="h-16 flex items-center px-5 bg-gradient-to-r from-srec-primary to-green-800 flex-shrink-0">
        <div className="w-8 h-8 rounded-lg bg-white/20 backdrop-blur-sm border border-white/30 flex items-center justify-center text-white font-extrabold text-sm shadow mr-3 flex-shrink-0">
          CV
        </div>
        <div>
          <h1 className="font-bold text-white tracking-tight text-sm leading-tight">CampusVoice</h1>
          <p className="text-[10px] text-green-200 uppercase tracking-widest font-semibold">Admin Panel</p>
        </div>
      </div>

      {/* Nav items */}
      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-0.5">
        <NavItem path="/admin" icon={LayoutDashboard} label="Dashboard" exact />
        <NavItem path="/admin/complaints" icon={FileText} label="All Complaints" />

        {/* Community accordion */}
        <div>
          <button
            onClick={() => setCommunityOpen(o => !o)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-150 border-l-[3px] border-transparent pl-2.5 ${
              isActive('/admin/petitions') || isActive('/admin/representatives')
                ? 'bg-srec-primarySoft text-srec-primary'
                : 'text-srec-textSecondary hover:bg-srec-backgroundAlt hover:text-srec-textPrimary'
            }`}
          >
            <Megaphone size={18} className={
              isActive('/admin/petitions') || isActive('/admin/representatives')
                ? 'text-srec-primary' : 'text-srec-textMuted'
            } strokeWidth={2} />
            <span className="text-sm font-medium flex-1 text-left">Community</span>
            <ChevronDown
              size={14}
              className={`transition-transform duration-200 ${communityOpen ? 'rotate-180' : ''}`}
            />
          </button>
          {communityOpen && (
            <div className="ml-4 mt-0.5 space-y-0.5 border-l border-srec-borderLight pl-2">
              <NavItem path="/admin/petitions" icon={ScrollText} label="Petitions" />
              <NavItem path="/admin/representatives" icon={UserCheck} label="Representatives" />
            </div>
          )}
        </div>

        <NavItem path="/admin/escalations" icon={TriangleAlert} label="Escalations" />
        <NavItem path="/admin/departments" icon={Building2} label="Departments" />

        {/* Users accordion */}
        <div>
          <button
            onClick={() => setUsersOpen(o => !o)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-150 border-l-[3px] border-transparent pl-2.5 ${
              isActive('/admin/students') || isActive('/admin/authorities')
                ? 'bg-srec-primarySoft text-srec-primary'
                : 'text-srec-textSecondary hover:bg-srec-backgroundAlt hover:text-srec-textPrimary'
            }`}
          >
            <Users size={18} className={
              isActive('/admin/students') || isActive('/admin/authorities')
                ? 'text-srec-primary' : 'text-srec-textMuted'
            } strokeWidth={2} />
            <span className="text-sm font-medium flex-1 text-left">Users</span>
            <ChevronDown
              size={14}
              className={`transition-transform duration-200 ${usersOpen ? 'rotate-180' : ''}`}
            />
          </button>

          {usersOpen && (
            <div className="ml-4 mt-0.5 space-y-0.5 border-l border-srec-borderLight pl-2">
              <NavItem path="/admin/students" icon={GraduationCap} label="Students" />
              <NavItem path="/admin/authorities" icon={ShieldCheck} label="Authorities" />
            </div>
          )}
        </div>

        <NavItem path="/admin/profile" icon={UserCog} label="Profile" />
      </nav>

      {/* User info + logout */}
      <div className="p-3 border-t border-srec-borderLight space-y-2 flex-shrink-0">
        <div className="flex items-center gap-3 bg-srec-primarySoft rounded-xl p-3 border border-srec-primaryMuted/30">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-srec-primary to-green-700 text-white text-sm font-bold flex items-center justify-center flex-shrink-0 shadow-sm">
            {initials}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-srec-textPrimary truncate leading-tight">{user?.name || 'Admin'}</p>
            <div className="flex items-center gap-1 mt-0.5">
              <ShieldCheck size={10} className="text-emerald-600 flex-shrink-0" />
              <p className="text-[10px] text-emerald-700 font-semibold truncate">{user?.authority_type || 'Super Admin'}</p>
            </div>
          </div>
        </div>

        <button
          onClick={handleLogout}
          className="flex items-center gap-2.5 w-full px-3 py-2.5 rounded-xl text-srec-textMuted hover:bg-red-50 hover:text-red-600 transition-colors text-sm font-medium"
        >
          <LogOut size={16} /> Sign Out
        </button>
      </div>
    </aside>
  );
}
