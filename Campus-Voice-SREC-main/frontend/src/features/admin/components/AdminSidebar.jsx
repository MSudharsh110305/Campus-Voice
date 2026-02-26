import React from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  FileText,
  Users,
  Building2,
  TriangleAlert,
  UserCog,
  LogOut,
  ShieldCheck
} from "lucide-react";
import { useAuth } from '../../../context/AuthContext';

export default function AdminSidebar({ className = "" }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const menuItems = [
    { name: "Dashboard",      path: "/admin",              icon: LayoutDashboard },
    { name: "All Complaints", path: "/admin/complaints",   icon: FileText },
    { name: "Authorities",    path: "/admin/authorities",  icon: Users },
    { name: "Escalations",    path: "/admin/escalations",  icon: TriangleAlert },
    { name: "Departments",    path: "/admin/departments",  icon: Building2 },
    { name: "Profile",        path: "/admin/profile",      icon: UserCog }
  ];

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  const initials = user?.name?.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || 'A';

  return (
    <aside className={`w-64 flex-shrink-0 flex flex-col bg-white border-r border-gray-100 shadow-sm ${className}`}>
      {/* Brand header — rich green gradient */}
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
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = item.path === '/admin'
            ? location.pathname === '/admin'
            : location.pathname.startsWith(item.path);

          return (
            <NavLink key={item.name} to={item.path}>
              <div className={`flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-150 ${
                isActive
                  ? 'bg-gradient-to-r from-srec-primary/10 to-emerald-50 text-srec-primary border-l-[3px] border-srec-primary pl-2.5'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900 border-l-[3px] border-transparent pl-2.5'
              }`}>
                <Icon size={18} className={isActive ? 'text-srec-primary' : 'text-gray-400'} strokeWidth={isActive ? 2.5 : 2} />
                <span className={`text-sm ${isActive ? 'font-semibold' : 'font-medium'}`}>{item.name}</span>
              </div>
            </NavLink>
          );
        })}
      </nav>

      {/* User info + logout */}
      <div className="p-3 border-t border-gray-100 space-y-2 flex-shrink-0">
        <div className="flex items-center gap-3 bg-gradient-to-br from-emerald-50 to-green-50 rounded-xl p-3 border border-emerald-100">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-srec-primary to-green-700 text-white text-sm font-bold flex items-center justify-center flex-shrink-0 shadow-sm">
            {initials}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-gray-900 truncate leading-tight">{user?.name || 'Admin'}</p>
            <div className="flex items-center gap-1 mt-0.5">
              <ShieldCheck size={10} className="text-emerald-600 flex-shrink-0" />
              <p className="text-[10px] text-emerald-700 font-semibold truncate">{user?.authority_type || 'Super Admin'}</p>
            </div>
          </div>
        </div>

        <button
          onClick={handleLogout}
          className="flex items-center gap-2.5 w-full px-3 py-2.5 rounded-xl text-gray-500 hover:bg-red-50 hover:text-red-600 transition-colors text-sm font-medium"
        >
          <LogOut size={16} /> Sign Out
        </button>
      </div>
    </aside>
  );
}
