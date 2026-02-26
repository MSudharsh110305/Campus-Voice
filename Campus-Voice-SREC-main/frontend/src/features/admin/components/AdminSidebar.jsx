import React from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  FileText,
  Users,
  Building2,
  TriangleAlert,
  UserCog,
  LogOut
} from "lucide-react";
import { useAuth } from '../../../context/AuthContext';

export default function AdminSidebar({ className = "" }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const menuItems = [
    { name: "Dashboard", path: "/admin", icon: LayoutDashboard },
    { name: "All Complaints", path: "/admin/complaints", icon: FileText },
    { name: "Authorities", path: "/admin/authorities", icon: Users },
    { name: "Escalations", path: "/admin/escalations", icon: TriangleAlert },
    { name: "Categories", path: "/admin/departments", icon: Building2 },
    { name: "Profile", path: "/admin/profile", icon: UserCog }
  ];

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <aside className={`bg-white border-r border-gray-200 shadow-sm w-64 flex-shrink-0 flex flex-col ${className}`}>
      <div className="h-16 flex items-center px-6 border-b border-gray-100">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-srec-primary to-srec-primaryHover flex items-center justify-center text-white font-bold shadow-md mr-3">
          CV
        </div>
        <div>
          <h1 className="font-bold text-gray-900 tracking-tight">CampusVoice</h1>
          <p className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold">Admin Panel</p>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = item.path === '/admin'
            ? location.pathname === '/admin'
            : location.pathname.startsWith(item.path);

          return (
            <NavLink key={item.name} to={item.path}>
              <div className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 ${isActive
                ? "bg-srec-primary/10 text-srec-primary shadow-inner"
                : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                }`}>
                <Icon
                  size={20}
                  className={isActive ? "text-srec-primary" : "text-gray-400"}
                />
                <span className="text-sm font-medium">{item.name}</span>
              </div>
            </NavLink>
          );
        })}
      </nav>

      <div className="p-4 border-t border-gray-100 space-y-3">
        {/* Real user info */}
        <div className="bg-srec-primary/5 rounded-xl p-3">
          <p className="text-xs text-gray-500 mb-0.5">Signed in as</p>
          <p className="text-sm font-semibold text-gray-900 truncate">{user?.name || 'Admin'}</p>
          <p className="text-xs text-srec-primary font-medium truncate">{user?.authority_type || 'Super Admin'}</p>
        </div>

        {/* Sign Out */}
        <button
          onClick={() => { logout(); navigate('/login'); }}
          className="flex items-center gap-3 w-full px-4 py-3 rounded-xl text-gray-500 hover:bg-red-50 hover:text-red-600 transition-colors text-sm font-medium"
        >
          <LogOut size={18} /> Sign Out
        </button>
      </div>
    </aside>
  );
}
