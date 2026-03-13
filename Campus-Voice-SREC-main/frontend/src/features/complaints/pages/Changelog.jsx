import React, { useState, useEffect, useCallback } from 'react';
import { TopNav } from '../../../components/Navbars';
import BottomNav from '../../../components/BottomNav';
import { Card, Skeleton } from '../../../components/UI';
import { useAuth } from '../../../context/AuthContext';
import complaintService from '../../../services/complaint.service';
import { CheckCircle2, ChevronDown, Inbox } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { useNavigate } from 'react-router-dom';

const LIMIT = 20;

export default function Changelog() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [entries, setEntries] = useState([]);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);

  const fetchPage = useCallback(async (offset, append = false) => {
    try {
      if (append) setLoadingMore(true);
      else setLoading(true);

      const data = await complaintService.getChangelog(offset, LIMIT);
      const newEntries = data?.entries || [];
      setTotal(data?.total || 0);
      setEntries(prev => append ? [...prev, ...newEntries] : newEntries);
    } catch (err) {
      setError(err.message || 'Failed to load changelog');
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, []);

  useEffect(() => {
    fetchPage(0, false);
  }, [fetchPage]);

  const loadMore = () => {
    const nextSkip = skip + LIMIT;
    setSkip(nextSkip);
    fetchPage(nextSkip, true);
  };

  const hasMore = entries.length < total;

  return (
    <div className="min-h-screen bg-srec-background">
      <TopNav />

      <div className="max-w-3xl mx-auto px-4 pt-4 pb-24 md:pl-24 animate-fadeIn">
        {/* Community tab bar */}
        <div className="flex gap-1 mb-4 bg-white/70 backdrop-blur-sm border border-white/60 rounded-xl p-1 shadow-sm">
          <button
            onClick={() => navigate('/petitions')}
            className="flex-1 py-2 rounded-lg text-xs font-semibold text-gray-500 hover:text-gray-800 hover:bg-gray-100/60 transition-all"
          >
            Petitions
          </button>
          <button
            className="flex-1 py-2 rounded-lg text-xs font-bold bg-srec-primary text-white shadow-sm transition-all"
          >
            Wins
          </button>
        </div>

        {/* Header */}
        <div className="mb-6 p-5 bg-gradient-to-r from-srec-primary via-green-800 to-emerald-700 rounded-2xl text-white shadow-md relative overflow-hidden">
          <div className="absolute inset-0 opacity-10 pointer-events-none select-none">
            <div className="absolute w-40 h-40 rounded-full bg-white -top-10 -right-10" />
            <div className="absolute w-24 h-24 rounded-full bg-white bottom-0 left-20" />
          </div>
          <div className="relative">
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle2 size={18} className="text-emerald-300" />
              <h1 className="text-lg font-bold tracking-tight">What's Fixed</h1>
            </div>
            <p className="text-sm text-emerald-200/80">
              Popular resolved complaints — issues that students upvoted and got fixed
            </p>
            <p className="text-xs text-emerald-300/70 mt-1">
              Rolling 7-day window — refreshes daily
            </p>
          </div>
        </div>

        {/* Content */}
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-28 rounded-2xl" />)}
          </div>
        ) : error ? (
          <div className="text-center py-16 bg-white rounded-2xl border border-srec-border shadow-card">
            <p className="text-red-600 text-sm font-medium">{error}</p>
          </div>
        ) : entries.length === 0 ? (
          <div className="text-center py-20 bg-white rounded-2xl border border-srec-border shadow-card">
            <div className="w-14 h-14 mx-auto mb-3 rounded-full bg-srec-backgroundAlt flex items-center justify-center">
              <Inbox size={26} className="text-srec-textMuted" />
            </div>
            <p className="text-srec-textPrimary font-semibold">No resolved complaints yet</p>
            <p className="text-srec-textMuted text-sm mt-1">Check back soon!</p>
          </div>
        ) : (
          <>
            <div className="space-y-3">
              {entries.map((entry) => (
                <Card key={entry.id} className="p-4 hover:shadow-card-hover transition-shadow duration-200">
                  <div className="flex items-start gap-3">
                    {/* Green check icon */}
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-green-100 flex items-center justify-center mt-0.5">
                      <CheckCircle2 size={15} className="text-green-600" />
                    </div>

                    <div className="flex-1 min-w-0">
                      {/* Category + date */}
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        {entry.category_name && (
                          <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-srec-primarySoft text-srec-primary">
                            {entry.category_name}
                          </span>
                        )}
                        {entry.resolved_at && (
                          <span className="text-[11px] text-srec-textMuted flex-shrink-0">
                            Resolved {formatDistanceToNow(new Date(entry.resolved_at), { addSuffix: true })}
                          </span>
                        )}
                      </div>

                      {/* Complaint text */}
                      <p className="text-sm text-srec-textSecondary leading-relaxed line-clamp-3">
                        {entry.rephrased_text}
                      </p>

                      {/* Resolution note */}
                      {entry.resolution_note && (
                        <div className="mt-2 pl-3 border-l-2 border-green-300">
                          <p className="text-xs text-green-800 font-medium">Authority note:</p>
                          <p className="text-xs text-green-700 italic mt-0.5">{entry.resolution_note}</p>
                        </div>
                      )}

                      {/* Footer: score badge + resolution speed + votes + satisfaction */}
                      <div className="flex items-center gap-3 mt-2.5 flex-wrap">
                        {entry.win_score != null && (
                          <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 border border-amber-200">
                            Score: {entry.win_score}
                          </span>
                        )}
                        {entry.resolution_hours != null && (
                          <span className="text-[11px] text-srec-textMuted">
                            {entry.resolution_hours < 24
                              ? `Resolved in ${Math.round(entry.resolution_hours)} hour${Math.round(entry.resolution_hours) !== 1 ? 's' : ''}`
                              : `Resolved in ${Math.round(entry.resolution_hours / 24)} day${Math.round(entry.resolution_hours / 24) !== 1 ? 's' : ''}`}
                          </span>
                        )}
                        <span className="text-xs text-srec-textMuted">
                          {entry.upvotes} upvote{entry.upvotes !== 1 ? 's' : ''}
                        </span>
                        {entry.satisfaction_avg != null && (
                          <span className="text-xs text-amber-600 font-medium flex items-center gap-0.5">
                            ★ {entry.satisfaction_avg.toFixed(1)}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>

            {hasMore && (
              <div className="flex justify-center mt-6">
                <button
                  onClick={loadMore}
                  disabled={loadingMore}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl border border-srec-border bg-white text-srec-textSecondary text-sm font-medium hover:bg-srec-backgroundAlt transition-colors disabled:opacity-60"
                >
                  {loadingMore ? 'Loading…' : (
                    <>Load more <ChevronDown size={15} /></>
                  )}
                </button>
              </div>
            )}

            <p className="text-center text-xs text-srec-textMuted mt-4">
              Showing {entries.length} of {total} resolved complaints
            </p>
          </>
        )}
      </div>

      {user?.role === 'Student' && <BottomNav />}
    </div>
  );
}
