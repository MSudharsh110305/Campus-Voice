import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import { Card, Skeleton, RaiseButton, Button, Select } from '../../../components/UI';
import { TopNav } from '../../../components/Navbars';
import BottomNav from '../../../components/BottomNav';
import ComplaintCard from '../components/ComplaintCard';
import NewComplaintModal from '../components/NewComplaintModal';
import complaintService from '../../../services/complaint.service';
import { AlertCircle, SlidersHorizontal, Search, X, Inbox } from 'lucide-react';
import { STATUSES, PRIORITIES, COMPLAINT_CATEGORIES } from '../../../utils/constants';

const initialFeed = [];

export default function StudentHome() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [feed, setFeed] = useState(initialFeed);
  const [activeTab, setActiveTab] = useState('feed'); // feed / mine
  const [showModal, setShowModal] = useState(false);
  const [skip, setSkip] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [myPostsLoading, setMyPostsLoading] = useState(false);

  // Filters for My Posts tab
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    status: 'All',
    priority: 'All',
    category_id: 'All',
    search: '',
  });

  useEffect(() => {
    fetchFeed();
  }, [activeTab, filters]);

  const fetchFeed = async () => {
    if (activeTab === 'feed') {
      try {
        setLoading(true);
        setSkip(0);
        setHasMore(true);

        let data;
        const hasActiveFilters = filters.status !== 'All' || filters.priority !== 'All' || filters.search !== '';

        if (hasActiveFilters) {
          const apiFilters = {
            skip: 0,
            limit: 20,
            ...(filters.status !== 'All' && { status: filters.status }),
            ...(filters.priority !== 'All' && { priority: filters.priority }),
            ...(filters.search !== '' && { search: filters.search })
          };
          data = await complaintService.getAdvancedFilteredComplaints(apiFilters);
        } else {
          data = await complaintService.getPublicFeed(0, 20);
        }

        if (Array.isArray(data)) {
          setFeed(data);
          setHasMore(data.length === 20);
        } else if (data && Array.isArray(data.complaints)) {
          setFeed(data.complaints);
          setHasMore(data.complaints.length === 20);
        } else if (data && Array.isArray(data.data)) {
          setFeed(data.data);
          setHasMore(data.data.length === 20);
        } else {
          setFeed([]);
          setHasMore(false);
        }
        setSkip(20);
      } catch (error) {
        console.error("Failed to load feed:", error);
      } finally {
        setLoading(false);
      }
    }
  };

  const loadMore = async () => {
    if (loadingMore || !hasMore) return;

    try {
      setLoadingMore(true);
      const data = await complaintService.getPublicFeed(skip, 20);

      let newComplaints = [];
      if (Array.isArray(data)) {
        newComplaints = data;
      } else if (data && Array.isArray(data.complaints)) {
        newComplaints = data.complaints;
      } else if (data && Array.isArray(data.data)) {
        newComplaints = data.data;
      }

      setFeed([...feed, ...newComplaints]);
      setSkip(skip + 20);
      setHasMore(newComplaints.length === 20);
    } catch (error) {
      console.error("Failed to load more:", error);
    } finally {
      setLoadingMore(false);
    }
  };

  const handleNewComplaint = (newComplaint) => {
    setFeed([newComplaint, ...feed]);
  };

  // Get first name only for greeting
  const firstName = user?.name?.split(' ')[0] || user?.roll_no || 'Student';

  return (
    <div className="min-h-screen bg-srec-background">
      <TopNav />
      <div className="animate-fadeIn max-w-3xl mx-auto px-4 pt-4 pb-24 md:pl-24 transition-all duration-300">

        {/* Greeting banner */}
        <div className="mb-5 rounded-2xl bg-gradient-to-br from-srec-primary via-green-800 to-emerald-700 px-5 py-4 shadow-md shadow-green-900/10 relative overflow-hidden">
          {/* Decorative ring */}
          <div className="absolute -top-6 -right-6 w-28 h-28 rounded-full bg-white/5 pointer-events-none" />
          <div className="absolute -bottom-8 -right-2 w-20 h-20 rounded-full bg-white/5 pointer-events-none" />
          <p className="text-green-200 text-xs font-medium mb-0.5 uppercase tracking-widest">SREC Campus Voice</p>
          <h2 className="text-xl font-bold text-white tracking-tight">
            Hello, {firstName} 👋
          </h2>
          <p className="text-green-300 text-xs mt-1">Here's what's happening on campus today</p>
        </div>

        {/* Campus Feed heading + filter toggle */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-gray-900 tracking-tight">Campus Feed</h2>
            {feed.length > 0 && !loading && (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                {feed.length}
              </span>
            )}
          </div>
          <Button
            variant="ghost"
            onClick={() => setShowFilters(!showFilters)}
            className={`gap-1.5 text-xs font-semibold rounded-lg px-3 py-1.5 transition-all ${
              showFilters
                ? 'bg-srec-primary text-white shadow-sm'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            <SlidersHorizontal size={14} />
            Filters
          </Button>
        </div>

        {showFilters && (
          <Card className="mb-5 p-4 border-srec-primary/10 bg-srec-primary/[0.02] shadow-neu-inset rounded-2xl animate-in fade-in slide-in-from-top-4 duration-300">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={14} />
                <input
                  type="text"
                  className="w-full bg-white border border-gray-200 rounded-xl py-2 pl-9 pr-3 text-xs focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary outline-none transition-all"
                  placeholder="Search keywords..."
                  value={filters.search}
                  onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                />
              </div>
              <Select
                options={['All', ...STATUSES]}
                value={filters.status}
                onChange={(val) => setFilters({ ...filters, status: val })}
                className="w-full bg-white shadow-sm text-xs"
              />
              <Select
                options={['All', ...PRIORITIES]}
                value={filters.priority}
                onChange={(val) => setFilters({ ...filters, priority: val })}
                className="w-full bg-white shadow-sm text-xs"
              />
              <Button
                variant="ghost"
                className="text-xs font-bold text-gray-400 hover:text-srec-danger h-[38px] border border-dashed border-gray-200 rounded-xl"
                onClick={() => setFilters({ status: 'All', priority: 'All', category_id: 'All', search: '' })}
              >
                <X size={12} className="mr-1" /> Reset
              </Button>
            </div>
          </Card>
        )}

        {loading && activeTab === 'feed' && (
          <div className="space-y-3">
            <Skeleton className="h-44 rounded-2xl" />
            <Skeleton className="h-44 rounded-2xl" />
          </div>
        )}

        <div className="space-y-3">
          {/* Raise an Issue CTA */}
          <RaiseButton
            onClick={() => navigate('/posts')}
            className="w-full"
          >
            <AlertCircle size={18} />
            Raise an Issue
          </RaiseButton>

          {!loading && feed.length === 0 ? (
            <div className="text-center py-14 bg-white rounded-2xl border border-gray-100 shadow-sm">
              <div className="w-14 h-14 mx-auto mb-3 rounded-full bg-emerald-50 flex items-center justify-center">
                <Inbox size={24} className="text-emerald-400" />
              </div>
              <p className="text-gray-800 text-base font-semibold">No posts yet</p>
              <p className="text-gray-400 text-sm mt-1 max-w-xs mx-auto">
                Be the first to raise a complaint for your campus
              </p>
            </div>
          ) : (
            <>
              {feed.map((item) => (
                <ComplaintCard
                  key={item.id || item.complaint_id}
                  id={item.id || item.complaint_id}
                  rephrased_text={item.rephrased_text}
                  summary={item.summary}
                  category={item.category_name || COMPLAINT_CATEGORIES[item.category_id]}
                  department_code={item.department_code}
                  has_image={item.has_image}
                  author={item.is_anonymous ? 'Anonymous' : (item.author || item.student_roll_no)}
                  status={item.status}
                  priority={item.priority}
                  upvotes={item.upvotes}
                  downvotes={item.downvotes}
                  timestamp={item.submitted_at}
                  assigned_authority_name={item.assigned_authority_name || null}
                />
              ))}

              {hasMore && !loading && (
                <div className="flex justify-center pt-2">
                  <button
                    onClick={loadMore}
                    disabled={loadingMore}
                    className="flex items-center gap-2 border border-emerald-200 bg-emerald-50 text-emerald-700 rounded-xl px-6 py-2 text-sm font-semibold hover:bg-emerald-100 hover:border-emerald-300 transition-all duration-200 disabled:opacity-50"
                  >
                    {loadingMore ? 'Loading...' : 'Load More'}
                  </button>
                </div>
              )}
            </>
          )}
        </div>

      </div>

      <NewComplaintModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        onSubmit={handleNewComplaint}
      />

      {user?.role === 'Student' && <BottomNav />}
    </div>
  );
}
