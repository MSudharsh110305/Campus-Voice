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

        {/* Clean greeting */}
        <div className="mb-5">
          <h2 className="text-xl font-bold text-gray-900 tracking-tight">
            Hello, {firstName}
          </h2>
          <p className="text-sm text-gray-400 mt-0.5">Here's what's happening on campus</p>
        </div>

        {/* Campus Feed heading + filter toggle */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-bold text-gray-900 tracking-tight">
            Campus Feed
          </h2>
          <Button
            variant="ghost"
            onClick={() => setShowFilters(!showFilters)}
            className={`gap-2 text-sm ${showFilters ? 'bg-srec-primary/10 text-srec-primary' : 'text-gray-500 hover:text-gray-900'}`}
          >
            <SlidersHorizontal size={16} />
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
            <div className="text-center py-16 bg-white rounded-2xl border border-gray-100 shadow-sm">
              <div className="w-14 h-14 mx-auto mb-3 rounded-full bg-gray-50 flex items-center justify-center">
                <Inbox size={26} className="text-gray-400" />
              </div>
              <p className="text-gray-700 text-base font-semibold">No posts yet</p>
              <p className="text-gray-400 text-sm mt-1 max-w-xs mx-auto">
                Be the first to raise a complaint
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
                />
              ))}

              {hasMore && !loading && (
                <div className="flex justify-center pt-2">
                  <button
                    onClick={loadMore}
                    disabled={loadingMore}
                    className="border border-gray-200 rounded-xl px-6 py-2 text-sm text-gray-600 hover:border-srec-primary hover:text-srec-primary transition-all duration-200"
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
