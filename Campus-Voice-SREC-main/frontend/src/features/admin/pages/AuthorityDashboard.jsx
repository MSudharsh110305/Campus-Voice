import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import authorityService from '../../../services/authority.service';
import complaintService from '../../../services/complaint.service';
import { tokenStorage } from '../../../utils/api';
import ExportModal from '../../../components/ExportModal';
import { Card, EliteButton, Select } from '../../../components/UI';
import StatsCard from '../../../components/UI/StatsCard';
import AuthoritySidebar from '../components/AuthoritySidebar';
import AuthorityHeader from '../components/AuthorityHeader';
import AuthorityComplaintCard from '../components/AuthorityComplaintCard';
import { STATUSES, VALID_STATUS_TRANSITIONS, REASON_REQUIRED_STATUSES } from '../../../utils/constants';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { LayoutDashboard, CheckCircle, Clock, AlertCircle, X, Download, TrendingUp, Paperclip, Menu } from 'lucide-react';

const ROLE_TITLES = {
  'Warden': 'Warden Dashboard',
  'Deputy Warden': 'Deputy Warden Dashboard',
  'Senior Deputy Warden': 'Sr. Deputy Warden Dashboard',
  'HOD': 'HOD Dashboard',
  'Admin Officer': 'Admin Officer Dashboard',
  'Disciplinary Committee': 'Disciplinary Committee',
  'Admin': 'Admin Dashboard',
};

// Generic modal backdrop
function Modal({ open, onClose, title, children }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <Card className="w-full max-w-md p-6 bg-white shadow-xl border-0">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-gray-900">{title}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>
        {children}
      </Card>
    </div>
  );
}

export default function AuthorityDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [dashboard, setDashboard] = useState(null);
  const [detailedStats, setDetailedStats] = useState(null);
  const [complaints, setComplaints] = useState([]);
  const [statusFilter, setStatusFilter] = useState('All');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalComplaints, setTotalComplaints] = useState(0);
  const PAGE_SIZE = 20;
  const [error, setError] = useState(null);
  const [showExport, setShowExport] = useState(false);

  // Status update modal
  const [statusModal, setStatusModal] = useState({ open: false, complaintId: null, currentStatus: null });
  const [newStatus, setNewStatus] = useState('');
  const [statusReason, setStatusReason] = useState('');
  const [statusSubmitting, setStatusSubmitting] = useState(false);

  // Post update modal
  const [postUpdateModal, setPostUpdateModal] = useState({ open: false, complaintId: null });
  const [updateTitle, setUpdateTitle] = useState('');
  const [updateContent, setUpdateContent] = useState('');
  const [postUpdateSubmitting, setPostUpdateSubmitting] = useState(false);

  // Escalate modal
  const [escalateModal, setEscalateModal] = useState({ open: false, complaintId: null });
  const [escalateReason, setEscalateReason] = useState('');
  const [escalateSubmitting, setEscalateSubmitting] = useState(false);

  // Attachment modal
  const [attachModal, setAttachModal] = useState({ open: false, complaintId: null });
  const [attachFile, setAttachFile] = useState(null);
  const [attachSubmitting, setAttachSubmitting] = useState(false);

  // Feedback messages
  const [feedback, setFeedback] = useState({ type: '', message: '' });

  useEffect(() => {
    if (!user) {
      navigate('/login');
      return;
    }
    if (user.role !== 'Authority' && user.role !== 'Admin') {
      setError('You do not have permission to access this dashboard');
      return;
    }
    loadDashboard();
  }, []);

  useEffect(() => {
    if (dashboard) {
      setCurrentPage(1);
      loadComplaints(1);
    }
  }, [statusFilter]);

  const showFeedback = (type, message) => {
    setFeedback({ type, message });
    setTimeout(() => setFeedback({ type: '', message: '' }), 4000);
  };

  const loadDashboard = async () => {
    try {
      setLoading(true);
      setError(null);
      const [data, detailed] = await Promise.all([
        authorityService.getDashboard(),
        authorityService.getDetailedStats().catch(() => null),
      ]);
      setDashboard(data);
      setDetailedStats(detailed);
      await loadComplaints(1);
    } catch (err) {
      setError(err.message || 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  const loadComplaints = async (page = currentPage) => {
    try {
      // 'Disputed' is a client-side pseudo-filter: load Spam, then filter by has_disputed
      const apiFilter = statusFilter === 'Disputed' ? 'Spam' : (statusFilter === 'All' ? null : statusFilter);
      const skip = (page - 1) * PAGE_SIZE;
      const data = await authorityService.getMyComplaints(skip, PAGE_SIZE, apiFilter);
      let list = [];
      let total = 0;
      if (Array.isArray(data)) {
        list = data;
        total = data.length < PAGE_SIZE ? skip + data.length : skip + PAGE_SIZE + 1;
      } else if (data?.complaints) {
        list = data.complaints;
        total = data.total ?? (list.length < PAGE_SIZE ? skip + list.length : skip + PAGE_SIZE + 1);
      } else if (data?.data) {
        list = data.data;
        total = data.total ?? (list.length < PAGE_SIZE ? skip + list.length : skip + PAGE_SIZE + 1);
      }
      if (statusFilter === 'Disputed') list = list.filter(c => c.has_disputed);
      setComplaints(list);
      setTotalComplaints(total);
    } catch (err) {
      console.error('Failed to load complaints:', err);
      setComplaints([]);
      setTotalComplaints(0);
    }
  };

  // --- Status Update ---
  const openStatusModal = (e, complaintId, currentStatus) => {
    e.stopPropagation();
    const validNext = VALID_STATUS_TRANSITIONS[currentStatus] || [];
    if (validNext.length === 0) return;
    setStatusModal({ open: true, complaintId, currentStatus });
    setNewStatus(validNext[0]);
    setStatusReason('');
  };

  const handleStatusUpdate = async () => {
    if (!newStatus) return;
    const needsReason = REASON_REQUIRED_STATUSES.includes(newStatus);
    if (needsReason && !statusReason.trim()) {
      showFeedback('error', `A reason is required when marking as "${newStatus}"`);
      return;
    }
    setStatusSubmitting(true);
    try {
      await authorityService.updateComplaintStatus(
        statusModal.complaintId, newStatus, statusReason.trim() || null
      );
      setStatusModal({ open: false, complaintId: null, currentStatus: null });
      showFeedback('success', `Status updated to "${newStatus}" successfully`);
      await loadComplaints(currentPage);
      await loadDashboard();
    } catch (err) {
      showFeedback('error', err.message || 'Failed to update status');
    } finally {
      setStatusSubmitting(false);
    }
  };

  // --- Post Update ---
  const openPostUpdateModal = (e, complaintId) => {
    e.stopPropagation();
    setPostUpdateModal({ open: true, complaintId });
    setUpdateTitle('');
    setUpdateContent('');
  };

  const handlePostUpdate = async () => {
    if (!updateTitle.trim() || !updateContent.trim()) {
      showFeedback('error', 'Both title and content are required for a public update');
      return;
    }
    setPostUpdateSubmitting(true);
    try {
      await authorityService.postUpdate(postUpdateModal.complaintId, updateTitle.trim(), updateContent.trim());
      setPostUpdateModal({ open: false, complaintId: null });
      showFeedback('success', 'Public update posted successfully');
      await loadComplaints(currentPage);
    } catch (err) {
      showFeedback('error', err.message || 'Failed to post update');
    } finally {
      setPostUpdateSubmitting(false);
    }
  };

  // --- Escalate ---
  const openEscalateModal = (e, complaintId) => {
    e.stopPropagation();
    setEscalateModal({ open: true, complaintId });
    setEscalateReason('');
  };

  const handleAttach = async () => {
    if (!attachFile) {
      showFeedback('error', 'Please select a file to attach');
      return;
    }
    setAttachSubmitting(true);
    try {
      await complaintService.uploadAuthorityAttachment(attachModal.complaintId, attachFile);
      setAttachModal({ open: false, complaintId: null });
      setAttachFile(null);
      showFeedback('success', 'File attached successfully');
    } catch (err) {
      showFeedback('error', err.message || 'Failed to upload attachment');
    } finally {
      setAttachSubmitting(false);
    }
  };

  const handleEscalate = async () => {
    if (!escalateReason.trim()) {
      showFeedback('error', 'A reason is required to escalate the complaint');
      return;
    }
    setEscalateSubmitting(true);
    try {
      await authorityService.escalateComplaint(escalateModal.complaintId, escalateReason.trim());
      setEscalateModal({ open: false, complaintId: null });
      showFeedback('success', 'Complaint escalated successfully');
      await loadComplaints(currentPage);
    } catch (err) {
      showFeedback('error', err.message || 'Failed to escalate complaint');
    } finally {
      setEscalateSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-srec-background flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-srec-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-500 font-medium">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-srec-background flex items-center justify-center">
        <Card className="p-8 max-w-md shadow-lg border-red-100">
          <div className="w-12 h-12 bg-red-50 rounded-full flex items-center justify-center mb-4 mx-auto text-srec-danger">
            <AlertCircle size={24} />
          </div>
          <h2 className="text-xl font-bold text-red-900 mb-2 text-center">Access Denied</h2>
          <p className="text-gray-600 mb-6 text-center">{error}</p>
          <EliteButton onClick={loadDashboard} className="w-full justify-center">Retry Connection</EliteButton>
        </Card>
      </div>
    );
  }

  const stats = dashboard?.stats || {};
  const validNextStatuses = statusModal.currentStatus
    ? VALID_STATUS_TRANSITIONS[statusModal.currentStatus] || []
    : [];

  // --- Detailed stats for charts ---
  const dsByPriority = detailedStats?.by_priority || {};
  const weeklyTrend = detailedStats?.weekly_trend || [];
  const resolutionRate = detailedStats?.resolution_rate ?? null;
  const avgResolutionHours = detailedStats?.avg_resolution_hours ?? null;

  const dashboardTitle = ROLE_TITLES[user?.authority_type] || `${user?.authority_type || 'Authority'} Dashboard`;

  const exportSections = [
    {
      id: 'performance',
      label: 'Performance Summary',
      stats: [
        { label: 'Total Assigned', value: stats.total_assigned || 0 },
        { label: 'In Progress', value: stats.in_progress || 0 },
        { label: 'Resolved', value: stats.resolved || 0 },
        { label: 'Pending / Raised', value: stats.pending || stats.raised || 0 },
        { label: 'Resolution Rate', value: resolutionRate != null ? `${Math.round(resolutionRate)}%` : '—' },
        { label: 'Avg Resolution Time', value: avgResolutionHours != null ? `${Math.round(avgResolutionHours)}h` : '—' },
      ],
    },
    ...(Object.keys(dsByPriority).length > 0 ? [{
      id: 'by_priority',
      label: 'Complaints by Priority',
      tableHeaders: ['Priority', 'Count'],
      tableRows: ['Critical', 'High', 'Medium', 'Low'].map(p => [p, dsByPriority[p] || 0]),
    }] : []),
    ...(weeklyTrend.length > 0 ? [{
      id: 'weekly_trend',
      label: 'Weekly Trend (Last 4 Weeks)',
      tableHeaders: ['Week', 'Count'],
      tableRows: weeklyTrend.map(w => [w.label, w.count]),
    }] : []),
  ];

  return (
    <div className="flex min-h-screen bg-srec-background">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 md:hidden backdrop-blur-sm"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <div className={`fixed inset-y-0 left-0 z-40 transform transition-transform duration-300 ease-in-out md:translate-x-0 md:static ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <AuthoritySidebar className="h-full" onClose={() => setSidebarOpen(false)} />
      </div>

      <div className="flex-1 md:ml-0 flex flex-col min-w-0 transition-all duration-300 overflow-hidden">
        <div className="flex items-center md:hidden h-14 px-4 bg-white border-b border-gray-100 sticky top-0 z-20">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 -ml-2 text-gray-500 hover:bg-gray-100 rounded-lg"
          >
            <Menu size={22} />
          </button>
          <span className="ml-3 font-bold text-srec-primary text-sm">CampusVoice</span>
        </div>
        <AuthorityHeader />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto animate-fadeIn">

          {/* Feedback banner */}
          {feedback.message && (
            <div className={`mb-4 p-4 rounded-xl text-sm font-medium flex items-center gap-2 ${
              feedback.type === 'success'
                ? 'bg-green-50 border border-green-100 text-green-700'
                : 'bg-red-50 border border-red-100 text-red-600'
            }`}>
              {feedback.type === 'success' ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
              {feedback.message}
            </div>
          )}

          {/* Dashboard Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{dashboardTitle}</h1>
              <p className="text-sm text-gray-500 mt-0.5">{user?.name} · {user?.authority_type}</p>
            </div>
            <div className="flex items-center gap-3">
              <EliteButton variant="outline" onClick={loadDashboard}>Refresh</EliteButton>
              <EliteButton onClick={() => setShowExport(true)} className="flex items-center gap-2">
                <Download size={16} /> Export
              </EliteButton>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            <StatsCard
              label="Total Assigned"
              value={stats.total_assigned || 0}
              icon={LayoutDashboard}
              color="blue"
              onClick={() => setStatusFilter('All')}
            />
            <StatsCard
              label="In Progress"
              value={stats.in_progress || 0}
              icon={Clock}
              color="yellow"
              onClick={() => setStatusFilter('In Progress')}
            />
            <StatsCard
              label="Resolved"
              value={stats.resolved || 0}
              icon={CheckCircle}
              color="green"
              onClick={() => setStatusFilter('Resolved')}
            />
            <StatsCard
              label="Pending"
              value={stats.pending || stats.raised || 0}
              icon={AlertCircle}
              color="red"
              onClick={() => setStatusFilter('Raised')}
            />
          </div>

          {/* Resolution metrics row */}
          {(resolutionRate != null || avgResolutionHours != null) && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
              <div className="bg-white/80 backdrop-blur-sm rounded-xl border border-white/60 p-4 shadow-[0_4px_16px_-4px_rgba(0,0,0,0.06)] text-center">
                <p className="text-2xl font-bold text-srec-primary font-heading">
                  {resolutionRate != null ? `${Math.round(resolutionRate)}%` : '—'}
                </p>
                <p className="text-xs text-gray-500 mt-1 font-medium">Resolution Rate</p>
              </div>
              <div className="bg-white/80 backdrop-blur-sm rounded-xl border border-white/60 p-4 shadow-[0_4px_16px_-4px_rgba(0,0,0,0.06)] text-center">
                <p className="text-2xl font-bold text-blue-600 font-heading">
                  {avgResolutionHours != null ? `${Math.round(avgResolutionHours)}h` : '—'}
                </p>
                <p className="text-xs text-gray-500 mt-1 font-medium">Avg Resolution Time</p>
              </div>
              {['Critical', 'High'].map(p => {
                const pColors = { Critical: 'text-red-600', High: 'text-orange-600' };
                return (
                  <div key={p} className="bg-white/80 backdrop-blur-sm rounded-xl border border-white/60 p-4 shadow-[0_4px_16px_-4px_rgba(0,0,0,0.06)] text-center">
                    <p className={`text-2xl font-bold ${pColors[p]} font-heading`}>{dsByPriority[p] || 0}</p>
                    <p className="text-xs text-gray-500 mt-1 font-medium">{p} Priority</p>
                  </div>
                );
              })}
            </div>
          )}

          {/* Charts */}
          {weeklyTrend.length > 0 && (
            <div className="mb-8">
              <Card className="p-6 shadow-[0_4px_24px_-4px_rgba(0,0,0,0.08)] border border-white/60 bg-white/80 backdrop-blur-sm">
                <h3 className="text-base font-bold text-gray-900 mb-4 flex items-center gap-2 font-heading">
                  <TrendingUp size={18} className="text-srec-primary" />
                  Weekly Complaint Trend
                </h3>
                <div className="h-48 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={weeklyTrend}>
                      <defs>
                        <linearGradient id="authColorCount" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#14532D" stopOpacity={0.15} />
                          <stop offset="95%" stopColor="#14532D" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                      <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fill: '#9CA3AF', fontSize: 11 }} />
                      <YAxis axisLine={false} tickLine={false} tick={{ fill: '#9CA3AF', fontSize: 11 }} />
                      <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }} />
                      <Area type="monotone" dataKey="count" stroke="#14532D" strokeWidth={2.5} fillOpacity={1} fill="url(#authColorCount)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </div>
          )}

          {/* Filter Section */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
            <h2 className="text-xl font-bold text-gray-900 tracking-tight">Assigned Complaints</h2>
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-500 font-medium">Filter by:</span>
              <Select
                value={statusFilter}
                onChange={setStatusFilter}
                options={[
                  { value: 'All', label: 'All Statuses' },
                  ...STATUSES.map(s => ({ value: s, label: s })),
                  { value: 'Disputed', label: '⚠ Disputed (Spam)' },
                ]}
                className="w-48 bg-white border-gray-200"
              />
            </div>
          </div>

          {/* Complaints List */}
          {complaints.length === 0 ? (
            <div className="bg-white rounded-2xl p-12 text-center border border-gray-100 shadow-sm">
              <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mb-4 mx-auto text-gray-400">
                <LayoutDashboard size={28} />
              </div>
              <h3 className="text-lg font-bold text-gray-900 mb-2">No complaints found</h3>
              <p className="text-gray-500 mb-6 max-w-md mx-auto">
                {statusFilter !== 'All'
                  ? `There are no complaints with status "${statusFilter}" currently assigned to you.`
                  : 'You have no complaints assigned at the moment.'}
              </p>
              <EliteButton variant="outline" onClick={loadDashboard}>
                Refresh Dashboard
              </EliteButton>
            </div>
          ) : (
            <>
              <div className="space-y-4">
                {complaints.map(complaint => (
                  <AuthorityComplaintCard
                    key={complaint.id}
                    complaint={complaint}
                    onStatusUpdate={openStatusModal}
                    onPostUpdate={openPostUpdateModal}
                    onEscalate={openEscalateModal}
                    onAttach={(e, id) => { e.stopPropagation(); setAttachModal({ open: true, complaintId: id }); setAttachFile(null); }}
                    token={tokenStorage.getAccessToken()}
                  />
                ))}
              </div>

              {/* Google-style pagination */}
              {(() => {
                const totalPages = Math.ceil(totalComplaints / PAGE_SIZE);
                if (totalPages <= 1) return null;
                const getPages = () => {
                  const pages = [];
                  if (totalPages <= 7) {
                    for (let i = 1; i <= totalPages; i++) pages.push(i);
                  } else {
                    pages.push(1);
                    if (currentPage > 4) pages.push('…');
                    const start = Math.max(2, currentPage - 2);
                    const end = Math.min(totalPages - 1, currentPage + 2);
                    for (let i = start; i <= end; i++) pages.push(i);
                    if (currentPage < totalPages - 3) pages.push('…');
                    pages.push(totalPages);
                  }
                  return pages;
                };
                const goTo = (p) => {
                  setCurrentPage(p);
                  loadComplaints(p);
                  window.scrollTo({ top: 0, behavior: 'smooth' });
                };
                return (
                  <div className="flex items-center justify-center gap-1 mt-8 flex-wrap">
                    <button
                      onClick={() => goTo(currentPage - 1)}
                      disabled={currentPage === 1}
                      className="px-3 py-1.5 rounded-lg text-sm font-medium border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      &lsaquo;
                    </button>
                    {getPages().map((p, i) =>
                      p === '…' ? (
                        <span key={`ellipsis-${i}`} className="px-2 py-1.5 text-gray-400 text-sm select-none">…</span>
                      ) : (
                        <button
                          key={p}
                          onClick={() => goTo(p)}
                          className={`min-w-[36px] px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                            currentPage === p
                              ? 'bg-srec-primary text-white border-srec-primary shadow-sm'
                              : 'border-gray-200 bg-white text-gray-700 hover:bg-gray-50 hover:border-srec-primary'
                          }`}
                        >
                          {p}
                        </button>
                      )
                    )}
                    <button
                      onClick={() => goTo(currentPage + 1)}
                      disabled={currentPage >= totalPages}
                      className="px-3 py-1.5 rounded-lg text-sm font-medium border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      &rsaquo;
                    </button>
                  </div>
                );
              })()}
            </>
          )}
        </main>
      </div>

      {/* Status Update Modal */}
      <Modal
        open={statusModal.open}
        onClose={() => setStatusModal({ open: false, complaintId: null, currentStatus: null })}
        title="Update Complaint Status"
      >
        <div className="space-y-4">
          <div>
            <p className="text-sm text-gray-500 mb-3">
              Current status: <span className="font-semibold text-gray-800">{statusModal.currentStatus}</span>
            </p>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">New Status *</label>
            <select
              className="w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-srec-primary/30 focus:border-srec-primary"
              value={newStatus}
              onChange={e => setNewStatus(e.target.value)}
            >
              {validNextStatuses.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          {(REASON_REQUIRED_STATUSES.includes(newStatus) || statusReason) && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Reason {REASON_REQUIRED_STATUSES.includes(newStatus) ? '*' : '(optional)'}
              </label>
              <textarea
                className="w-full border border-gray-200 rounded-lg p-3 text-sm focus:ring-2 focus:ring-srec-primary/30 focus:border-srec-primary outline-none resize-none bg-gray-50 focus:bg-white"
                rows={3}
                placeholder={
                  newStatus === 'Spam' ? 'Reason for flagging as spam...' :
                  newStatus === 'Closed' ? 'Reason for closing...' :
                  'Optional reason for status change...'
                }
                value={statusReason}
                onChange={e => setStatusReason(e.target.value)}
              />
            </div>
          )}

          {!REASON_REQUIRED_STATUSES.includes(newStatus) && !statusReason && (
            <p className="text-xs text-gray-400">
              Optionally provide a reason for this status change.
              <button className="ml-1 text-srec-primary underline" onClick={() => setStatusReason(' ')}>
                Add reason
              </button>
            </p>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <EliteButton
              variant="outline"
              onClick={() => setStatusModal({ open: false, complaintId: null, currentStatus: null })}
              disabled={statusSubmitting}
            >
              Cancel
            </EliteButton>
            <EliteButton
              variant="primary"
              onClick={handleStatusUpdate}
              disabled={statusSubmitting}
              isLoading={statusSubmitting}
            >
              {statusSubmitting ? 'Updating...' : 'Update Status'}
            </EliteButton>
          </div>
        </div>
      </Modal>

      {/* Post Public Update Modal */}
      <Modal
        open={postUpdateModal.open}
        onClose={() => setPostUpdateModal({ open: false, complaintId: null })}
        title="Post Public Update"
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-500">
            This update will be visible to the student and all who can view this complaint.
          </p>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Title *</label>
            <input
              type="text"
              className="w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-srec-primary/30 focus:border-srec-primary"
              placeholder="Update title (e.g. Investigation started)"
              value={updateTitle}
              onChange={e => setUpdateTitle(e.target.value)}
              maxLength={200}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Content *</label>
            <textarea
              className="w-full border border-gray-200 rounded-lg p-3 text-sm focus:ring-2 focus:ring-srec-primary/30 focus:border-srec-primary outline-none resize-none bg-gray-50 focus:bg-white"
              rows={4}
              placeholder="Describe the update or action taken..."
              value={updateContent}
              onChange={e => setUpdateContent(e.target.value)}
              maxLength={2000}
            />
            <p className="text-xs text-gray-400 mt-1">{updateContent.length} / 2000</p>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <EliteButton
              variant="outline"
              onClick={() => setPostUpdateModal({ open: false, complaintId: null })}
              disabled={postUpdateSubmitting}
            >
              Cancel
            </EliteButton>
            <EliteButton
              variant="primary"
              onClick={handlePostUpdate}
              disabled={postUpdateSubmitting}
              isLoading={postUpdateSubmitting}
            >
              {postUpdateSubmitting ? 'Posting...' : 'Post Update'}
            </EliteButton>
          </div>
        </div>
      </Modal>

      {/* Escalate Modal */}
      <Modal
        open={escalateModal.open}
        onClose={() => setEscalateModal({ open: false, complaintId: null })}
        title="Escalate Complaint"
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-500">
            Escalating will forward this complaint to a higher authority. Please provide a reason.
          </p>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Reason *</label>
            <textarea
              className="w-full border border-gray-200 rounded-lg p-3 text-sm focus:ring-2 focus:ring-srec-primary/30 focus:border-srec-primary outline-none resize-none bg-gray-50 focus:bg-white"
              rows={3}
              placeholder="Why does this need to be escalated? (e.g. requires senior authority approval...)"
              value={escalateReason}
              onChange={e => setEscalateReason(e.target.value)}
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <EliteButton
              variant="outline"
              onClick={() => setEscalateModal({ open: false, complaintId: null })}
              disabled={escalateSubmitting}
            >
              Cancel
            </EliteButton>
            <EliteButton
              variant="danger"
              onClick={handleEscalate}
              disabled={escalateSubmitting}
              isLoading={escalateSubmitting}
            >
              {escalateSubmitting ? 'Escalating...' : 'Escalate'}
            </EliteButton>
          </div>
        </div>
      </Modal>

      {/* Attach File Modal */}
      <Modal
        open={attachModal.open}
        onClose={() => { setAttachModal({ open: false, complaintId: null }); setAttachFile(null); }}
        title="Attach File to Complaint"
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-500">
            Upload a supporting document (PDF, Excel, Word) or image. Max 10MB.
          </p>
          <label className="block">
            <span className="block text-sm font-medium text-gray-700 mb-1.5">Select File</span>
            <div className="border-2 border-dashed border-gray-200 rounded-xl p-6 text-center cursor-pointer hover:border-srec-primary/40 transition-colors">
              <input
                type="file"
                className="hidden"
                id="attach-file-input"
                accept=".pdf,.xlsx,.xls,.docx,.doc,.png,.jpg,.jpeg,.webp,.gif"
                onChange={e => setAttachFile(e.target.files[0] || null)}
              />
              <label htmlFor="attach-file-input" className="cursor-pointer">
                <Paperclip size={24} className="mx-auto mb-2 text-gray-400" />
                {attachFile ? (
                  <p className="text-sm font-semibold text-srec-primary">{attachFile.name}</p>
                ) : (
                  <p className="text-sm text-gray-500">Click to browse or drag & drop</p>
                )}
                <p className="text-xs text-gray-400 mt-1">PDF, Excel, Word, PNG, JPG, WebP — max 10MB</p>
              </label>
            </div>
          </label>
          <div className="flex justify-end gap-3 pt-2">
            <EliteButton
              variant="outline"
              onClick={() => { setAttachModal({ open: false, complaintId: null }); setAttachFile(null); }}
              disabled={attachSubmitting}
            >
              Cancel
            </EliteButton>
            <EliteButton
              variant="primary"
              onClick={handleAttach}
              disabled={attachSubmitting || !attachFile}
              isLoading={attachSubmitting}
            >
              {attachSubmitting ? 'Uploading...' : 'Upload & Attach'}
            </EliteButton>
          </div>
        </div>
      </Modal>

      {/* Export Modal */}
      <ExportModal
        isOpen={showExport}
        onClose={() => setShowExport(false)}
        title={`${dashboardTitle} — Export`}
        sections={exportSections}
      />
    </div>
  );
}
