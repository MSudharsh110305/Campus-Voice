import React, { useState, useEffect } from 'react';
import { TopNav } from '../../../components/Navbars';
import BottomNav from '../../../components/BottomNav';
import { useAuth } from '../../../context/AuthContext';
import studentService from '../../../services/student.service';
import ComplaintCard from '../components/ComplaintCard';
import { Select, Button, Skeleton, Card } from '../../../components/UI';
import { STATUSES, PRIORITIES, CATEGORY_LIST, COMPLAINT_CATEGORIES } from '../../../utils/constants';
import { FileX, Search, X, SlidersHorizontal, Calendar, AlertTriangle, FileText, CheckCircle, Clock } from 'lucide-react';
import complaintService from '../../../services/complaint.service';
import { tokenStorage } from '../../../utils/api';
import { Link, useSearchParams } from 'react-router-dom';

const STATUS_TABS = ['All', 'Raised', 'In Progress', 'Resolved', 'Closed', 'Spam'];

export default function MyComplaints() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [complaints, setComplaints] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [skip, setSkip] = useState(0);
  const LIMIT = 20;

  // Tab filter — initialize from URL param on mount
  const urlStatus = searchParams.get('status') || 'All';
  const initialTab = STATUS_TABS.includes(urlStatus) ? urlStatus : 'All';
  const [activeStatusTab, setActiveStatusTab] = useState(initialTab);

  // Advanced Filters State
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    status: 'All',
    priority: 'All',
    category_id: 'All',
    search: '',
    date_from: '',
    date_to: '',
  });

  useEffect(() => {
    studentService.getStats().then(setStats).catch(() => {});
  }, []);

  useEffect(() => {
    fetchComplaints();
  }, [filters, skip, activeStatusTab]);

  const fetchComplaints = async () => {
    try {
      setLoading(true);

      const statusArg = activeStatusTab !== 'All' ? activeStatusTab : (filters.status !== 'All' ? filters.status : undefined);
      const data = await studentService.getMyComplaints({ skip, limit: LIMIT, status_filter: statusArg });

      if (data && Array.isArray(data.complaints)) {
        setComplaints(data.complaints);
      } else {
        setComplaints([]);
      }
    } catch (error) {
      console.error("Failed to fetch complaints", error);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (name, val) => {
    setFilters(prev => ({ ...prev, [name]: val }));
    setSkip(0);
  };

  const resetFilters = () => {
    setFilters({
      status: 'All',
      priority: 'All',
      category_id: 'All',
      search: '',
      date_from: '',
      date_to: '',
    });
    setSkip(0);
  };

  const handleDisputeSpam = async (complaintId) => {
    const reason = window.prompt('Why do you think this is not spam? (Optional — press OK to skip)');
    if (reason === null) return; // user pressed Cancel
    try {
      const token = tokenStorage.getAccessToken();
      const url = `/api/complaints/${complaintId}/appeal-spam${reason ? `?reason=${encodeURIComponent(reason)}` : ''}`;
      const res = await fetch(url, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json().catch(() => ({}));
      alert(data.message || (res.ok ? 'Dispute submitted successfully.' : 'Failed to submit dispute.'));
    } catch {
      alert('Failed to submit dispute. Please try again.');
    }
  };

  return (
    <div className="min-h-screen bg-srec-background">
      <TopNav />
      <main className="animate-fadeIn max-w-4xl mx-auto px-4 pt-4 pb-24">

        {/* Page banner */}
        <div className="mb-4 rounded-2xl bg-gradient-to-br from-srec-primary via-green-800 to-emerald-700 px-5 py-4 shadow-md shadow-green-900/10 relative overflow-hidden">
          <div className="absolute -top-6 -right-6 w-24 h-24 rounded-full bg-white/5 pointer-events-none" />
          <div className="flex items-center justify-between">
            <div>
              <p className="text-green-200 text-[10px] font-semibold uppercase tracking-widest mb-0.5">My Activity</p>
              <h1 className="text-xl font-bold text-white tracking-tight">My Complaints</h1>
              <p className="text-green-300 text-xs mt-0.5">Track and manage your raised issues</p>
            </div>
            <Button
              className={`flex items-center gap-1.5 text-xs font-semibold rounded-xl px-3 py-2 transition-all flex-shrink-0 ${
                showFilters ? 'bg-white text-srec-primary shadow-sm' : 'bg-white/10 text-white border border-white/20 hover:bg-white/20'
              }`}
              onClick={() => setShowFilters(!showFilters)}
            >
              <SlidersHorizontal size={14} />
              Filters
              {(filters.priority !== 'All' || filters.category_id !== 'All' || filters.search || filters.date_from || filters.date_to) && (
                <span className="w-2 h-2 bg-amber-400 rounded-full" />
              )}
            </Button>
          </div>
        </div>

        {/* Stat Cards — clickable to filter */}
        <div className="grid grid-cols-3 gap-3 mb-4">
          <button
            onClick={() => { setActiveStatusTab('All'); setSkip(0); setSearchParams({}); }}
            className={`rounded-xl p-3 text-center border transition-all overflow-hidden relative ${activeStatusTab === 'All' ? 'bg-srec-primary text-white border-srec-primary shadow-sm' : 'bg-white border-gray-100 hover:border-srec-primary/40'}`}
          >
            {activeStatusTab === 'All' && <div className="absolute inset-0 bg-gradient-to-br from-srec-primary to-green-700 -z-0" />}
            <div className={`relative flex items-center justify-center gap-1 mb-0.5 ${activeStatusTab === 'All' ? 'text-white/80' : 'text-gray-400'}`}>
              <FileText size={12} />
            </div>
            <div className={`relative text-xl font-bold leading-none ${activeStatusTab === 'All' ? 'text-white' : 'text-gray-900'}`}>{stats?.total_complaints ?? 0}</div>
            <div className={`relative text-[10px] mt-0.5 ${activeStatusTab === 'All' ? 'text-white/80' : 'text-gray-500'}`}>Total</div>
          </button>
          <button
            onClick={() => { setActiveStatusTab('Resolved'); setSkip(0); setSearchParams({ status: 'Resolved' }); }}
            className={`rounded-xl p-3 text-center border transition-all ${activeStatusTab === 'Resolved' ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm' : 'bg-white border-gray-100 hover:border-emerald-200'}`}
          >
            <div className={`flex items-center justify-center gap-1 mb-0.5 ${activeStatusTab === 'Resolved' ? 'text-white/80' : 'text-emerald-500'}`}>
              <CheckCircle size={12} />
            </div>
            <div className={`text-xl font-bold leading-none ${activeStatusTab === 'Resolved' ? 'text-white' : 'text-emerald-700'}`}>{stats?.resolved ?? 0}</div>
            <div className={`text-[10px] mt-0.5 ${activeStatusTab === 'Resolved' ? 'text-white/80' : 'text-gray-500'}`}>Resolved</div>
          </button>
          <button
            onClick={() => { setActiveStatusTab('Raised'); setSkip(0); setSearchParams({ status: 'Raised' }); }}
            className={`rounded-xl p-3 text-center border transition-all ${activeStatusTab === 'Raised' ? 'bg-amber-500 text-white border-amber-500 shadow-sm' : 'bg-white border-gray-100 hover:border-amber-200'}`}
          >
            <div className={`flex items-center justify-center gap-1 mb-0.5 ${activeStatusTab === 'Raised' ? 'text-white/80' : 'text-amber-500'}`}>
              <Clock size={12} />
            </div>
            <div className={`text-xl font-bold leading-none ${activeStatusTab === 'Raised' ? 'text-white' : 'text-amber-600'}`}>{(stats?.raised ?? 0) + (stats?.in_progress ?? 0)}</div>
            <div className={`text-[10px] mt-0.5 ${activeStatusTab === 'Raised' ? 'text-white/80' : 'text-gray-500'}`}>Pending</div>
          </button>
        </div>

        {/* Status pill tabs */}
        <div className="flex gap-2 overflow-x-auto pb-1 mb-4 scrollbar-none">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => {
                setActiveStatusTab(tab);
                setSkip(0);
                if (tab === 'All') {
                  setSearchParams({});
                } else {
                  setSearchParams({ status: tab });
                }
              }}
              className={`flex-shrink-0 px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-200 ${
                activeStatusTab === tab
                  ? 'bg-srec-primary text-white shadow-sm'
                  : 'bg-white text-gray-500 border border-gray-200 hover:border-srec-primary/40 hover:text-srec-primary'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Search Bar */}
        <div className="relative mb-4">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
          <input
            type="text"
            placeholder="Search complaints..."
            className="w-full bg-white rounded-xl border border-gray-200 py-2.5 pl-11 pr-4 text-sm focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary transition-all outline-none text-gray-700"
            value={filters.search}
            onChange={(e) => handleFilterChange('search', e.target.value)}
          />
        </div>

        {/* Advanced Filter Panel */}
        {showFilters && (
          <Card className="p-5 border-srec-primary/10 bg-srec-primary/[0.02] shadow-neu-inset rounded-2xl mb-4 animate-in fade-in slide-in-from-top-4 duration-300">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Priority</label>
                <Select
                  options={['All', ...PRIORITIES]}
                  value={filters.priority}
                  onChange={(val) => handleFilterChange('priority', val)}
                  className="w-full bg-white shadow-sm text-sm"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Category</label>
                <Select
                  options={[
                    { value: 'All', label: 'All Categories' },
                    ...CATEGORY_LIST.map(c => ({ value: c.id, label: c.name }))
                  ]}
                  value={filters.category_id}
                  onChange={(val) => handleFilterChange('category_id', val)}
                  className="w-full bg-white shadow-sm text-sm"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Date From</label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={13} />
                  <input
                    type="date"
                    className="w-full bg-white border border-gray-200 rounded-xl py-2 pl-9 pr-3 text-sm focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary outline-none transition-all"
                    value={filters.date_from}
                    onChange={(e) => handleFilterChange('date_from', e.target.value)}
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Date To</label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={13} />
                  <input
                    type="date"
                    className="w-full bg-white border border-gray-200 rounded-xl py-2 pl-9 pr-3 text-sm focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary outline-none transition-all"
                    value={filters.date_to}
                    onChange={(e) => handleFilterChange('date_to', e.target.value)}
                  />
                </div>
              </div>
              <div className="flex items-end">
                <Button
                  variant="ghost"
                  className="w-full h-[40px] text-xs font-bold text-gray-400 hover:text-srec-danger border border-dashed border-gray-200 rounded-xl"
                  onClick={resetFilters}
                >
                  <X size={13} className="mr-1" /> Reset Filters
                </Button>
              </div>
            </div>
          </Card>
        )}

        {loading ? (
          <div className="space-y-3">
            <Skeleton className="h-44 rounded-2xl" />
            <Skeleton className="h-44 rounded-2xl" />
          </div>
        ) : (
          <div className="space-y-3">
            {complaints.length === 0 ? (
              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-12 text-center">
                <div className="w-14 h-14 mx-auto mb-3 rounded-full bg-gray-50 flex items-center justify-center">
                  <FileX size={26} className="text-gray-400" />
                </div>
                <p className="text-gray-700 font-semibold text-base">No complaints yet</p>
                <p className="text-gray-400 text-sm mt-1 max-w-xs mx-auto">
                  Your submitted complaints will appear here
                </p>
                <Link
                  to="/posts"
                  className="inline-block mt-4 text-sm text-srec-primary font-semibold hover:underline"
                >
                  Submit a complaint
                </Link>
              </div>
            ) : (
              complaints.map((c) => (
                <div key={c.id || c.complaint_id}>
                  {/* Spam banner shown above the card for spam complaints */}
                  {(c.is_marked_as_spam || c.status === 'Spam') && (
                    <div className="mb-1 flex items-center justify-between bg-red-50 border border-red-200 rounded-xl px-4 py-2.5">
                      <div className="flex items-center gap-2 text-red-700">
                        <AlertTriangle size={14} />
                        <span className="text-xs font-semibold">Flagged as Spam</span>
                        {c.spam_reason && (
                          <span className="text-xs text-red-500 truncate max-w-[160px]">— {c.spam_reason}</span>
                        )}
                      </div>
                      <button
                        onClick={() => handleDisputeSpam(c.id || c.complaint_id)}
                        className="text-xs font-semibold text-red-700 border border-red-300 rounded-lg px-3 py-1 hover:bg-red-100 transition-colors flex-shrink-0"
                      >
                        Dispute
                      </button>
                    </div>
                  )}
                  <ComplaintCard
                    id={c.id || c.complaint_id}
                    desc={c.rephrased_text || c.original_text}
                    category={c.category_name || COMPLAINT_CATEGORIES[c.category_id]}
                    has_image={c.has_image}
                    author={c.is_anonymous ? 'Anonymous' : (c.author || c.student_roll_no)}
                    status={c.status}
                    priority={c.priority}
                    upvotes={c.upvotes}
                    downvotes={c.downvotes}
                    timestamp={c.submitted_at || c.created_at}
                    isOwner={true}
                    assigned_authority_name={c.assigned_authority_name || null}
                    location_verified={c.location_verified || false}
                  />
                </div>
              ))
            )}
          </div>
        )}

        {/* Simple Pagination */}
        {complaints.length > 0 && (
          <div className="flex justify-between items-center mt-6 pt-4 border-t border-gray-100">
            <button
              className="text-sm text-gray-500 hover:text-srec-primary disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              disabled={skip === 0}
              onClick={() => setSkip(Math.max(0, skip - LIMIT))}
            >
              ← Previous
            </button>
            <span className="text-xs text-gray-400 bg-gray-50 px-3 py-1 rounded-full border border-gray-100">
              Page {Math.floor(skip / LIMIT) + 1}
            </span>
            <button
              className="text-sm text-gray-500 hover:text-srec-primary disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              disabled={complaints.length < LIMIT}
              onClick={() => setSkip(skip + LIMIT)}
            >
              Next →
            </button>
          </div>
        )}
      </main>

      {user?.role === 'Student' && <BottomNav />}
    </div>
  );
}
