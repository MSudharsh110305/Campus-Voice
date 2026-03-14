import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import { Card, Skeleton, RaiseButton, Button, Select } from '../../../components/UI';
import { TopNav } from '../../../components/Navbars';
import BottomNav from '../../../components/BottomNav';
import ComplaintCard from '../components/ComplaintCard';
import NewComplaintModal from '../components/NewComplaintModal';
import complaintService from '../../../services/complaint.service';
import usePullToRefresh from '../../../hooks/usePullToRefresh';
import {
  AlertCircle, SlidersHorizontal, Search, X, Inbox, RefreshCw,
} from 'lucide-react';
import { STATUSES, PRIORITIES, COMPLAINT_CATEGORIES } from '../../../utils/constants';

// ─────────────────────────── helpers ────────────────────────────────────────
const extractComplaints = (data) => {
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.complaints)) return data.complaints;
  if (data && Array.isArray(data.data)) return data.data;
  return [];
};

const SCROLL_KEY = 'cv_feed_scroll';
const FEED_CACHE_KEY = 'cv_feed_cache';

// ═══════════════════════ Main Component ═════════════════════════════════════
export default function StudentHome() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const sentinelRef = useRef(null);
  const observerRef = useRef(null);

  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState(() => {
    try {
      const saved = sessionStorage.getItem('cv_feed_filters');
      if (saved) return { status: 'All', priority: 'All', category_id: 'All', search: '', sortBy: 'hot', ...JSON.parse(saved) };
    } catch {}
    return { status: 'All', priority: 'All', category_id: 'All', search: '', sortBy: 'hot' };
  });

  // Feed state — try to restore from cache first
  const [feed, setFeed] = useState([]);
  const [skip, setSkip] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  const firstName = user?.name?.split(' ')[0] || user?.roll_no || 'Student';

  // ── Pull-to-refresh ──────────────────────────────────────────────────────
  const { refreshing, pullProgress, pullDistance, handlers: pullHandlers } = usePullToRefresh(
    async () => {
      sessionStorage.removeItem(FEED_CACHE_KEY);
      sessionStorage.removeItem(SCROLL_KEY);
      await fetchFeed();
    },
    { threshold: 80 }
  );

  // ── Feed fetch ─────────────────────────────────────────────────────────────
  const fetchFeed = useCallback(async () => {
    try {
      setLoading(true);
      setSkip(0);
      setHasMore(true);
      let data;
      const hasTextFilters = filters.status !== 'All' || filters.priority !== 'All' || filters.search !== '';
      if (hasTextFilters) {
        const apiFilters = {
          skip: 0, limit: 20,
          ...(filters.status !== 'All' && { status: filters.status }),
          ...(filters.priority !== 'All' && { priority: filters.priority }),
          ...(filters.search !== '' && { search: filters.search }),
          ...(filters.category_id !== 'All' && { category_id: filters.category_id }),
        };
        data = await complaintService.getAdvancedFilteredComplaints(apiFilters);
      } else {
        data = await complaintService.getPublicFeed(0, 20, {
          categoryId: filters.category_id,
          sortBy: filters.sortBy,
        });
      }
      const complaints = extractComplaints(data);
      setFeed(complaints);
      setHasMore(complaints.length === 20);
      setSkip(20);
    } catch (err) {
      console.error('Feed error:', err);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  const loadMore = useCallback(async () => {
    if (loadingMore || !hasMore) return;
    try {
      setLoadingMore(true);
      const data = await complaintService.getPublicFeed(skip, 20, {
        categoryId: filters.category_id, sortBy: filters.sortBy,
      });
      const more = extractComplaints(data);
      setFeed(prev => [...prev, ...more]);
      setSkip(s => s + 20);
      setHasMore(more.length === 20);
    } finally {
      setLoadingMore(false);
    }
  }, [loadingMore, hasMore, skip, filters]);

  // ── Mount: try to restore cached feed + scroll position ───────────────────
  useEffect(() => {
    try {
      const cache = sessionStorage.getItem(FEED_CACHE_KEY);
      if (cache) {
        const { feed: cachedFeed, skip: cachedSkip, hasMore: cachedHasMore, filterKey } = JSON.parse(cache);
        const currentFilterKey = JSON.stringify({ sortBy: filters.sortBy, category_id: filters.category_id });
        if (filterKey === currentFilterKey && cachedFeed?.length > 0) {
          setFeed(cachedFeed);
          setSkip(cachedSkip);
          setHasMore(cachedHasMore);
          setLoading(false);
          // Restore scroll after paint
          requestAnimationFrame(() => {
            requestAnimationFrame(() => {
              const savedY = parseInt(sessionStorage.getItem(SCROLL_KEY) || '0', 10);
              if (savedY > 0) {
                window.scrollTo({ top: savedY, behavior: 'instant' });
                sessionStorage.removeItem(SCROLL_KEY);
              }
            });
          });
          return;
        }
      }
    } catch {}
    // No valid cache — normal fetch
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Fetch when filters change (skip on initial mount if cache restored) ───
  useEffect(() => {
    try {
      sessionStorage.setItem('cv_feed_filters', JSON.stringify({ sortBy: filters.sortBy, category_id: filters.category_id }));
    } catch {}
    // Clear cache on filter change
    sessionStorage.removeItem(FEED_CACHE_KEY);
    fetchFeed();
  }, [filters]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Save feed to cache whenever it changes ────────────────────────────────
  useEffect(() => {
    if (!loading && feed.length > 0) {
      try {
        const filterKey = JSON.stringify({ sortBy: filters.sortBy, category_id: filters.category_id });
        sessionStorage.setItem(FEED_CACHE_KEY, JSON.stringify({ feed, skip, hasMore, filterKey }));
      } catch {}
    }
  }, [feed, skip, hasMore]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Save scroll position on scroll ───────────────────────────────────────
  useEffect(() => {
    let ticking = false;
    const onScroll = () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          try { sessionStorage.setItem(SCROLL_KEY, window.scrollY.toString()); } catch {}
          ticking = false;
        });
        ticking = true;
      }
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // ── IntersectionObserver for infinite scroll ──────────────────────────────
  useEffect(() => {
    if (observerRef.current) observerRef.current.disconnect();
    if (!sentinelRef.current || !hasMore || loading) return;

    observerRef.current = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) loadMore(); },
      { rootMargin: '200px' }
    );
    observerRef.current.observe(sentinelRef.current);
    return () => observerRef.current?.disconnect();
  }, [hasMore, loading, loadMore]);

  return (
    <div className="min-h-screen bg-srec-background" {...pullHandlers}>
      <TopNav />

      {/* Pull-to-refresh indicator */}
      {(pullDistance > 0 || refreshing) && (
        <div className="flex items-center justify-center py-2 transition-all" style={{ height: refreshing ? 40 : pullDistance * 0.5 }}>
          <RefreshCw
            size={18}
            className={`text-srec-primary transition-transform ${refreshing ? 'animate-spin' : ''}`}
            style={{ opacity: pullProgress, transform: `rotate(${pullProgress * 360}deg)` }}
          />
        </div>
      )}

      <div className="animate-fadeIn max-w-3xl mx-auto px-4 pt-4 pb-24 md:pl-24 transition-all duration-300">

        {/* Greeting banner */}
        <div className="mb-4 rounded-2xl bg-gradient-to-br from-srec-primary via-green-800 to-emerald-700 px-5 py-4 shadow-elevated shadow-green-900/10 relative overflow-hidden">
          <div className="absolute -top-8 -right-8 w-32 h-32 rounded-full bg-white/5 pointer-events-none" />
          <div className="absolute -bottom-10 -right-3 w-24 h-24 rounded-full bg-white/5 pointer-events-none" />
          <p className="text-emerald-300/70 text-[10px] font-semibold mb-1 uppercase tracking-[0.2em]">SREC Campus Voice</p>
          <h2 className="text-xl font-bold text-white tracking-tight font-heading">Hello, {firstName}</h2>
          <p className="text-green-300/80 text-xs mt-1">Here&apos;s what&apos;s happening on campus today</p>
        </div>

        {/* Feed header + filter toggle */}
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-bold text-gray-900 font-heading">Campus Feed</h2>
          <Button
            variant="ghost"
            onClick={() => setShowFilters(!showFilters)}
            className={`gap-1.5 text-xs font-semibold rounded-lg px-3 py-1.5 transition-all ${
              showFilters ? 'bg-srec-primary text-white shadow-sm' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            <SlidersHorizontal size={14} />Filters
          </Button>
        </div>

        {/* Sort tabs */}
        <div className="flex gap-1.5 mb-4">
          {[{ key: 'hot', label: 'Hot' }, { key: 'new', label: 'New' }, { key: 'top', label: 'Top' }].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setFilters(f => ({ ...f, sortBy: key }))}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all border ${
                filters.sortBy === key
                  ? 'bg-srec-primary text-white border-srec-primary shadow-sm'
                  : 'bg-white text-gray-600 border-gray-200 hover:border-srec-primary hover:text-srec-primary'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {showFilters && (
          <Card className="mb-5 p-4 border-srec-borderLight bg-srec-backgroundAlt shadow-inner-soft rounded-2xl animate-slide-up">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={14} />
                <input
                  type="text"
                  className="w-full bg-white border border-gray-200 rounded-xl py-2 pl-9 pr-3 text-xs focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary outline-none transition-all"
                  placeholder="Search or paste short code…"
                  value={filters.search}
                  onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                />
              </div>
              <Select options={['All', ...STATUSES]} value={filters.status} onChange={(val) => setFilters({ ...filters, status: val })} className="w-full bg-white shadow-sm text-xs" />
              <Select options={['All', ...PRIORITIES]} value={filters.priority} onChange={(val) => setFilters({ ...filters, priority: val })} className="w-full bg-white shadow-sm text-xs" />
              <select value={filters.category_id} onChange={(e) => setFilters({ ...filters, category_id: e.target.value })} className="w-full bg-white border border-gray-200 rounded-xl py-2 px-3 text-xs focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary outline-none transition-all">
                <option value="All">All Categories</option>
                <option value="1">General</option>
                <option value="2">Department</option>
                <option value="3">Men&apos;s Hostel</option>
                <option value="4">Women&apos;s Hostel</option>
                <option value="5">Disciplinary Committee</option>
              </select>
              <Button variant="ghost" className="text-xs font-bold text-gray-400 hover:text-srec-danger h-[38px] border border-dashed border-gray-200 rounded-xl sm:col-span-2 lg:col-span-4" onClick={() => setFilters({ status: 'All', priority: 'All', category_id: 'All', search: '', sortBy: 'hot' })}>
                <X size={12} className="mr-1" /> Reset All Filters
              </Button>
            </div>
          </Card>
        )}

        {/* Feed content */}
        {loading ? (
          <div className="space-y-3">
            <Skeleton className="h-44 rounded-2xl" />
            <Skeleton className="h-44 rounded-2xl" />
          </div>
        ) : (
          <div className="space-y-3">
            <RaiseButton onClick={() => navigate('/posts')} className="w-full">
              <AlertCircle size={18} /> Raise an Issue
            </RaiseButton>

            {feed.length === 0 ? (
              <div className="text-center py-14 bg-white/80 backdrop-blur-sm rounded-2xl border border-white/60 shadow-[0_4px_24px_-4px_rgba(0,0,0,0.08)]">
                <div className="w-14 h-14 mx-auto mb-3 rounded-full bg-srec-primarySoft flex items-center justify-center">
                  <Inbox size={24} className="text-srec-primary" />
                </div>
                <p className="text-gray-900 text-base font-semibold">No posts yet</p>
                <p className="text-gray-500 text-sm mt-1">Be the first to raise a complaint for your campus</p>
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
                    image_required={item.image_required}
                    image_pending={item.image_pending}
                    author={item.is_anonymous ? 'Anonymous' : (item.author || item.student_roll_no)}
                    status={item.status}
                    priority={item.priority}
                    upvotes={item.upvotes}
                    downvotes={item.downvotes}
                    timestamp={item.submitted_at}
                    assigned_authority_name={item.assigned_authority_name || null}
                    isOwner={!!(user?.roll_no && item.student_roll_no === user.roll_no)}
                    location_verified={item.location_verified || false}
                  />
                ))}

                {/* Infinite scroll sentinel */}
                <div ref={sentinelRef} className="h-1" />

                {loadingMore && (
                  <div className="flex justify-center py-4">
                    <div className="w-6 h-6 border-2 border-srec-primary border-t-transparent rounded-full animate-spin" />
                  </div>
                )}

                {!hasMore && feed.length > 0 && (
                  <p className="text-center text-xs text-gray-400 py-4">You&apos;ve seen all complaints</p>
                )}
              </>
            )}
          </div>
        )}

      </div>

      <NewComplaintModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        onSubmit={(c) => setFeed(prev => [c, ...prev])}
      />

      {user?.role === 'Student' && <BottomNav />}
    </div>
  );
}
