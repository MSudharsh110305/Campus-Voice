import React, { useState, useEffect } from 'react';
import { TopNav } from '../../../components/Navbars';
import BottomNav from '../../../components/BottomNav';
import { Card, Button } from '../../../components/UI';
import { useAuth } from '../../../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import studentService from '../../../services/student.service';
import { LogOut, User, Mail, Hash, Building, BookOpen, Edit2, Lock, X, CheckCircle, Smartphone } from 'lucide-react';
import { DEPARTMENT_BY_ID } from '../../../utils/constants';

export default function Profile() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  // Modals state
  const [showEdit, setShowEdit] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // Edit Form State — only fields students can update: name, email, year
  // NOTE: Students do NOT have a phone column. Do NOT send phone.
  const [editForm, setEditForm] = useState({ name: '', email: '', year: '' });

  // Password Form State
  const [passForm, setPassForm] = useState({
    old_password: '',
    new_password: '',
    confirm_password: '',
  });

  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [isInstalled, setIsInstalled] = useState(
    () => window.matchMedia('(display-mode: standalone)').matches || !!window.navigator.standalone
  );
  const [showIosHint, setShowIosHint] = useState(false);

  useEffect(() => {
    fetchProfile();
    fetchStats();
  }, []);

  const fetchProfile = async () => {
    try {
      const data = await studentService.getProfile();
      setProfile(data);
      setEditForm({
        name: data.name || '',
        email: data.email || '',
        year: data.year || '',
      });
    } catch (err) {
      console.error('Failed to fetch profile', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const data = await studentService.getStats();
      setStats(data);
    } catch (err) {
      console.error('Failed to fetch stats', err);
    }
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    // Validate email domain
    if (editForm.email && !editForm.email.toLowerCase().endsWith('@srec.ac.in')) {
      setError('Email must be a valid @srec.ac.in address');
      return;
    }

    setActionLoading(true);
    try {
      // studentService.updateProfile strips phone and only sends allowed fields
      const updated = await studentService.updateProfile(editForm);
      setProfile(updated);
      setSuccess('Profile updated successfully!');
      setTimeout(() => {
        setShowEdit(false);
        setSuccess('');
      }, 1500);
    } catch (err) {
      setError(err.message || 'Failed to update profile');
    } finally {
      setActionLoading(false);
    }
  };

  const handleInstall = async () => {
    const prompt = window._deferredInstallPrompt;
    if (prompt) {
      prompt.prompt();
      const { outcome } = await prompt.userChoice;
      if (outcome === 'accepted') {
        setIsInstalled(true);
        window._deferredInstallPrompt = null;
      }
    } else if (/iphone|ipad|ipod/i.test(navigator.userAgent)) {
      setShowIosHint(v => !v);
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (passForm.new_password !== passForm.confirm_password) {
      setError('New passwords do not match');
      return;
    }

    // Basic password strength check
    if (!/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}/.test(passForm.new_password)) {
      setError('New password must be min 8 chars with uppercase, lowercase, and digit');
      return;
    }

    setActionLoading(true);
    try {
      await studentService.changePassword(passForm);
      setSuccess('Password changed successfully!');
      setPassForm({ old_password: '', new_password: '', confirm_password: '' });
      setTimeout(() => {
        setShowPassword(false);
        setSuccess('');
      }, 1500);
    } catch (err) {
      setError(err.message || 'Failed to change password');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) return (
    <div className="min-h-screen bg-srec-background flex items-center justify-center">
      <div className="w-8 h-8 border-4 border-srec-primary border-t-transparent rounded-full animate-spin" />
    </div>
  );

  const displayUser = profile || user; // Fallback to auth context user

  const deptInfo = displayUser?.department_id ? DEPARTMENT_BY_ID[displayUser.department_id] : null;
  const deptDisplay = displayUser?.department_name || deptInfo?.name || deptInfo?.code || 'N/A';

  return (
    <div className="min-h-screen bg-srec-background">
      <TopNav />
      <div className="max-w-2xl mx-auto p-4 sm:p-6 pb-24 md:pl-24 transition-all duration-300">
        <h1 className="text-2xl font-bold text-gray-900 mb-6 tracking-tight">Your Profile</h1>

        <Card className="shadow-neu-flat overflow-hidden">
          <div className="bg-gradient-to-r from-srec-primary to-srec-primaryLight h-32 relative">
            <div className="absolute -bottom-10 left-6 p-1 bg-srec-card rounded-full">
              <div className="w-20 h-20 rounded-full bg-slate-200 border-4 border-white flex items-center justify-center text-slate-500 font-bold text-3xl shadow-md">
                {displayUser?.name?.[0]?.toUpperCase() || 'U'}
              </div>
            </div>
            <div className="absolute top-4 right-4 flex gap-2">
              <Button variant="ghost" className="bg-white/20 hover:bg-white/30 text-white border-0" onClick={() => setShowEdit(true)}>
                <Edit2 size={16} className="mr-2" /> Edit
              </Button>
            </div>
          </div>

          <div className="pt-12 px-6 pb-8">
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-900">{displayUser?.name || 'User Name'}</h2>
              <div className="flex flex-wrap items-center gap-2 mt-1">
                <p className="text-gray-500 text-sm">{displayUser?.email || 'email@example.com'}</p>
                <span className="inline-block h-1 w-1 bg-gray-300 rounded-full"></span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-md bg-srec-primary/10 text-srec-primary uppercase tracking-wide">
                  {displayUser?.role || 'Student'}
                </span>
                {displayUser?.year && (
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-md bg-gray-100 text-gray-600">
                    Year {displayUser.year}
                  </span>
                )}
              </div>
            </div>

            {/* Stats Row */}
            {stats && (
              <div className="grid grid-cols-4 gap-2 mb-6 p-4 bg-gray-50 rounded-xl border border-gray-100">
                <div className="text-center">
                  <div className="text-xl font-bold text-gray-900">{stats.total_complaints || 0}</div>
                  <div className="text-xs text-gray-500">Total</div>
                </div>
                <div className="text-center">
                  <div className="text-xl font-bold text-amber-600">{stats.in_progress || 0}</div>
                  <div className="text-xs text-gray-500">In Progress</div>
                </div>
                <div className="text-center">
                  <div className="text-xl font-bold text-green-600">{stats.resolved || 0}</div>
                  <div className="text-xs text-gray-500">Resolved</div>
                </div>
                <div className="text-center">
                  <div className="text-xl font-bold text-gray-500">{stats.closed || 0}</div>
                  <div className="text-xs text-gray-500">Closed</div>
                </div>
              </div>
            )}

            <div className="border-t border-gray-100 pt-6 space-y-6">
              <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4">Personal Details</h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-6 gap-x-4 text-sm">
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-gray-50 text-gray-400"><Hash size={18} /></div>
                  <div>
                    <span className="block text-gray-500 text-xs">Register Number</span>
                    <span className="font-medium text-gray-900 block mt-0.5">{displayUser?.roll_no || 'N/A'}</span>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-gray-50 text-gray-400"><User size={18} /></div>
                  <div>
                    <span className="block text-gray-500 text-xs">Gender</span>
                    <span className="font-medium text-gray-900 block mt-0.5">{displayUser?.gender || 'N/A'}</span>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-gray-50 text-gray-400"><BookOpen size={18} /></div>
                  <div>
                    <span className="block text-gray-500 text-xs">Department</span>
                    <span className="font-medium text-gray-900 block mt-0.5">{deptDisplay}</span>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-gray-50 text-gray-400"><Building size={18} /></div>
                  <div>
                    <span className="block text-gray-500 text-xs">Stay Type</span>
                    <span className="font-medium text-gray-900 block mt-0.5 capitalize">{displayUser?.stay_type || 'N/A'}</span>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-gray-50 text-gray-400"><Mail size={18} /></div>
                  <div>
                    <span className="block text-gray-500 text-xs">Email</span>
                    <span className="font-medium text-gray-900 block mt-0.5">{displayUser?.email || 'N/A'}</span>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-gray-50 text-gray-400"><CheckCircle size={18} /></div>
                  <div>
                    <span className="block text-gray-500 text-xs">Account Status</span>
                    <span className={`font-medium block mt-0.5 ${displayUser?.is_active ? 'text-green-600' : 'text-red-500'}`}>
                      {displayUser?.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="pt-6 border-t border-gray-100 flex flex-col gap-3">
                <Button
                  variant="outline"
                  className="w-full flex items-center justify-center gap-2 py-3"
                  onClick={() => setShowPassword(true)}
                >
                  <Lock size={18} />
                  Change Password
                </Button>
                {!isInstalled && (window._deferredInstallPrompt || /iphone|ipad|ipod/i.test(navigator.userAgent)) && (
                  <div>
                    <Button
                      variant="outline"
                      className="w-full flex items-center justify-center gap-2 py-3"
                      onClick={handleInstall}
                    >
                      <Smartphone size={18} />
                      Install App
                    </Button>
                    {showIosHint && (
                      <p className="text-xs text-gray-500 text-center mt-2 px-2">
                        Tap the <strong>Share</strong> button in Safari, then choose <strong>"Add to Home Screen"</strong>.
                      </p>
                    )}
                  </div>
                )}
                {isInstalled && (
                  <div className="w-full flex items-center justify-center gap-2 py-3 rounded-2xl border border-emerald-200 text-emerald-600 bg-emerald-50 text-sm font-medium">
                    <Smartphone size={18} /> App Installed
                  </div>
                )}
                <button
                  onClick={() => { logout(); navigate('/login'); }}
                  className="w-full flex items-center justify-center gap-2 py-3 rounded-2xl border border-red-200 text-red-600 hover:bg-red-50 active:bg-red-100 transition-colors font-medium mt-6"
                >
                  <LogOut size={18} /> Sign Out
                </button>
              </div>
            </div>
          </div>
        </Card>
      </div>
      {user?.role === 'Student' && <BottomNav />}

      {/* Edit Profile Modal */}
      {showEdit && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex justify-center items-center p-4 animate-fadeIn">
          <div className="bg-srec-card rounded-2xl shadow-2xl w-full max-w-md border border-white/60 p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold text-gray-900">Edit Profile</h2>
              <button onClick={() => setShowEdit(false)} className="text-gray-400 hover:text-gray-600"><X size={24} /></button>
            </div>
            {error && <div className="p-3 mb-4 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100">{error}</div>}
            {success && <div className="p-3 mb-4 bg-green-50 text-green-600 text-sm rounded-lg border border-green-100">{success}</div>}
            <form onSubmit={handleEditSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
                <input
                  className="w-full rounded-lg border border-gray-300 p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-srec-primary/50"
                  value={editForm.name}
                  onChange={e => setEditForm({ ...editForm, name: e.target.value })}
                  placeholder="Your full name"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input
                  type="email"
                  className="w-full rounded-lg border border-gray-300 p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-srec-primary/50"
                  value={editForm.email}
                  onChange={e => setEditForm({ ...editForm, email: e.target.value })}
                  placeholder="student@srec.ac.in"
                />
                <p className="text-xs text-gray-400 mt-1">Must end with @srec.ac.in</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Year (1-10)</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  className="w-full rounded-lg border border-gray-300 p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-srec-primary/50"
                  value={editForm.year}
                  onChange={e => setEditForm({ ...editForm, year: e.target.value })}
                  placeholder="Academic year"
                />
              </div>
              <p className="text-xs text-amber-600 bg-amber-50 p-2 rounded-lg border border-amber-100">
                Note: Roll number, department, gender, and stay type cannot be changed after registration.
              </p>
              <div className="pt-2">
                <Button type="submit" className="w-full" isLoading={actionLoading} disabled={actionLoading}>
                  {actionLoading ? 'Saving...' : 'Save Changes'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Change Password Modal */}
      {showPassword && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex justify-center items-center p-4 animate-fadeIn">
          <div className="bg-srec-card rounded-2xl shadow-2xl w-full max-w-md border border-white/60 p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold text-gray-900">Change Password</h2>
              <button onClick={() => setShowPassword(false)} className="text-gray-400 hover:text-gray-600"><X size={24} /></button>
            </div>
            {error && <div className="p-3 mb-4 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100">{error}</div>}
            {success && <div className="p-3 mb-4 bg-green-50 text-green-600 text-sm rounded-lg border border-green-100">{success}</div>}
            <form onSubmit={handlePasswordSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Current Password</label>
                <input
                  type="password"
                  className="w-full rounded-lg border border-gray-300 p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-srec-primary/50"
                  value={passForm.old_password}
                  onChange={e => setPassForm({ ...passForm, old_password: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">New Password</label>
                <input
                  type="password"
                  className="w-full rounded-lg border border-gray-300 p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-srec-primary/50"
                  value={passForm.new_password}
                  onChange={e => setPassForm({ ...passForm, new_password: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Confirm New Password</label>
                <input
                  type="password"
                  className="w-full rounded-lg border border-gray-300 p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-srec-primary/50"
                  value={passForm.confirm_password}
                  onChange={e => setPassForm({ ...passForm, confirm_password: e.target.value })}
                />
              </div>
              <p className="text-xs text-gray-400">Min 8 chars with uppercase, lowercase, and digit.</p>
              <div className="pt-2">
                <Button type="submit" className="w-full" isLoading={actionLoading} disabled={actionLoading}>
                  {actionLoading ? 'Updating...' : 'Update Password'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
