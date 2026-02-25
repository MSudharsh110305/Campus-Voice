import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { StatusBadge, PriorityBadge } from '../../../components/UI';
import { useAuth } from '../../../context/AuthContext';
import complaintService from '../../../services/complaint.service';
import { ThumbsUp, ThumbsDown, Sparkles, FileX, ShieldCheck } from 'lucide-react';
import { Skeleton } from '../../../components/UI';

import { VOTE_TYPES } from '../../../utils/constants';

export default function ComplaintCard({
  id,
  title,
  desc,
  summary,
  rephrased_text,
  category,
  department_code,
  img,
  author,
  status,
  priority,
  upvotes,
  downvotes,
  timestamp,
  isOwner = false,
  has_image = false,
  assigned_authority_name = null
}) {
  const { user } = useAuth();
  const [expanded, setExpanded] = useState(false);
  const [voteCount, setVoteCount] = useState({ up: upvotes || 0, down: downvotes || 0 });
  const [userVote, setUserVote] = useState(null);
  const [isVoting, setIsVoting] = useState(false);
  const [voteError, setVoteError] = useState(null);
  const [imageUrl, setImageUrl] = useState(null);
  const [imageLoading, setImageLoading] = useState(false);

  const TRUNCATE_LEN = 150;
  const bodyText = isOwner ? null : (rephrased_text || summary || desc || '');
  const isLong = bodyText && bodyText.length > TRUNCATE_LEN;

  const showVoteError = (msg) => {
    setVoteError(msg);
    setTimeout(() => setVoteError(null), 3000);
  };

  // Fetch user's existing vote on mount - with delay to prevent rate limiting
  // Skip fetching if user is the complaint owner
  useEffect(() => {
    if (isOwner) {
      setUserVote(null);
      return;
    }

    const fetchMyVote = async () => {
      try {
        const voteData = await complaintService.getMyVote(id);
        setUserVote(voteData.has_voted ? voteData.vote_type : null);
      } catch (error) {
        console.log("Could not fetch vote status:", error.message);
      }
    };

    const delay = Math.random() * 500;
    const timer = setTimeout(fetchMyVote, delay);
    return () => clearTimeout(timer);
  }, [id, isOwner]);

  // Fetch image as blob on mount if exists - with delay to prevent rate limiting
  useEffect(() => {
    let active = true;
    if (has_image) {
      setImageLoading(true);

      const delay = Math.random() * 800;
      const timer = setTimeout(() => {
        complaintService.fetchImage(id, true)
          .then(url => {
            if (active) setImageUrl(url);
          })
          .catch(err => {
            console.log("Could not fetch thumbnail:", err.message);
            if (active) setImageUrl(null);
          })
          .finally(() => {
            if (active) setImageLoading(false);
          });
      }, delay);

      return () => {
        clearTimeout(timer);
        active = false;
        if (imageUrl) {
          URL.revokeObjectURL(imageUrl);
        }
      };
    } else {
      setImageUrl(null);
    }

    return () => {
      active = false;
      if (imageUrl) {
        URL.revokeObjectURL(imageUrl);
      }
    };
  }, [id, has_image]);

  // Update vote counts when props change
  useEffect(() => {
    setVoteCount({ up: upvotes || 0, down: downvotes || 0 });
  }, [upvotes, downvotes]);

  const handleVote = async (e, type) => {
    e.preventDefault();
    if (!user?.roll_no) {
      showVoteError("Please login to vote");
      return;
    }
    if (isVoting) return;

    setIsVoting(true);

    const prevVote = userVote;
    const prevCount = { ...voteCount };

    const isRemoving = userVote === type;
    let newUp = voteCount.up;
    let newDown = voteCount.down;

    if (isRemoving) {
      if (type === VOTE_TYPES.UPVOTE) newUp--;
      else newDown--;
      setUserVote(null);
    } else {
      if (prevVote === VOTE_TYPES.UPVOTE) newUp--;
      if (prevVote === VOTE_TYPES.DOWNVOTE) newDown--;
      if (type === VOTE_TYPES.UPVOTE) newUp++;
      else newDown++;
      setUserVote(type);
    }

    setVoteCount({ up: Math.max(0, newUp), down: Math.max(0, newDown) });

    try {
      let response;

      if (isRemoving) {
        response = await complaintService.removeVote(id);
      } else {
        response = await complaintService.voteOnComplaint(id, type);
      }

      setVoteCount({
        up: response.upvotes,
        down: response.downvotes
      });
      setUserVote(response.user_vote);

    } catch (error) {
      console.error("Vote failed:", error);

      setVoteCount(prevCount);
      setUserVote(prevVote);

      const errMsg = error?.response?.data?.error || error?.response?.data?.detail || '';
      const errorMsg = (errMsg || error.message || '').toLowerCase();
      if (errMsg.toLowerCase().includes('own') || errMsg.toLowerCase().includes('cannot vote') || error?.response?.status === 403 || error?.status === 403) {
        showVoteError("You can't vote on your own complaint");
      } else if (errorMsg.includes('greenlet') || errorMsg.includes('sqlalchemy')) {
        showVoteError("Server is temporarily busy. Please try again in a moment.");
      } else if (errorMsg.includes('rate limit')) {
        showVoteError("Too many requests. Please wait a moment and try again.");
      } else {
        showVoteError("Vote could not be registered. Please try again.");
      }
    } finally {
      setIsVoting(false);
    }
  };

  const displayContent = isOwner ? null : (rephrased_text || summary || desc);

  // Time ago helper
  const timeAgo = (ts) => {
    if (!ts) return '';
    const now = Date.now();
    const diff = now - new Date(ts).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    if (days < 7) return `${days}d ago`;
    return new Date(ts).toLocaleDateString();
  };

  return (
    <Link to={`/complaint/${id}`} className="block group">
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden transition-all duration-200 hover:shadow-neu-hover hover:-translate-y-0.5 cursor-pointer">
        {has_image && (
          <div className="relative h-44 overflow-hidden bg-gray-100">
            {imageLoading ? (
              <Skeleton className="w-full h-full" />
            ) : imageUrl ? (
              <img
                src={imageUrl}
                alt={title}
                className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
              />
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-gray-400">
                <FileX size={28} strokeWidth={1.5} />
                <span className="text-xs mt-1">Image failed to load</span>
              </div>
            )}
            <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent opacity-60"></div>
          </div>
        )}

        <div className="p-4">
          {/* Top row: category chip left, status badge right */}
          <div className="flex items-center justify-between gap-2 mb-2.5">
            <div className="flex items-center gap-1.5 flex-wrap">
              {category && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-srec-primary/10 text-srec-primary border border-srec-primary/20">
                  {category}
                </span>
              )}
            </div>
            <StatusBadge status={status || 'Raised'} />
          </div>

          {/* Title */}
          {title && (
            <h3 className="font-semibold text-gray-900 text-sm mb-1.5 leading-snug group-hover:text-srec-primary transition-colors line-clamp-1">{title}</h3>
          )}

          {/* Content — expandable */}
          {isOwner ? (
            <div className="mb-3">
              <p className="text-gray-500 text-sm leading-relaxed">{desc || summary}</p>
            </div>
          ) : (
            <div className="mb-3" onClick={(e) => { e.preventDefault(); e.stopPropagation(); }}>
              <p className="text-gray-500 text-sm leading-relaxed">
                {expanded || !isLong ? bodyText : bodyText.slice(0, TRUNCATE_LEN) + '…'}
              </p>
              {isLong && (
                <button
                  onClick={(e) => { e.preventDefault(); e.stopPropagation(); setExpanded(v => !v); }}
                  className="text-xs text-srec-primary font-semibold mt-1 hover:underline"
                >
                  {expanded ? 'Show less' : 'Read more'}
                </button>
              )}
            </div>
          )}

          {/* Handled by — only shown to the complaint owner */}
          {isOwner && assigned_authority_name && (
            <div className="flex items-center gap-1.5 mb-3 -mt-1">
              <ShieldCheck size={13} className="text-gray-400 flex-shrink-0" />
              <span className="text-xs text-gray-500">
                Handled by: <span className="font-medium text-gray-700">{assigned_authority_name}</span>
              </span>
            </div>
          )}

          {/* Footer: timestamp left, priority badge right */}
          <div className="flex items-center justify-between pt-3 border-t border-gray-100">
            <span className="text-xs text-gray-400">{timeAgo(timestamp)}</span>
            <PriorityBadge priority={priority || 'Low'} />
          </div>

          {/* Vote row */}
          <div className="flex items-center gap-2 mt-3">
            {isOwner ? (
              <span className="text-xs text-gray-400 italic">Your complaint</span>
            ) : (
              <>
                <button
                  onClick={(e) => handleVote(e, VOTE_TYPES.UPVOTE)}
                  disabled={isVoting}
                  className={`
                    flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold
                    transition-all duration-200
                    ${userVote === VOTE_TYPES.UPVOTE
                      ? 'bg-srec-primary text-white shadow-sm'
                      : 'bg-gray-50 text-gray-600 border border-gray-200 hover:bg-srec-primary/10 hover:border-srec-primary/30 hover:text-srec-primary hover:shadow-vote-glow'
                    }
                    active:scale-95
                  `}
                  title="Upvote"
                >
                  <ThumbsUp size={12} className={userVote === VOTE_TYPES.UPVOTE ? 'fill-current' : ''} />
                  <span>{voteCount.up}</span>
                </button>

                <button
                  onClick={(e) => handleVote(e, VOTE_TYPES.DOWNVOTE)}
                  disabled={isVoting}
                  className={`
                    flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold
                    transition-all duration-200
                    ${userVote === VOTE_TYPES.DOWNVOTE
                      ? 'bg-srec-danger text-white shadow-sm'
                      : 'bg-gray-50 text-gray-600 border border-gray-200 hover:bg-srec-danger/5 hover:border-srec-danger/30 hover:text-srec-danger'
                    }
                    active:scale-95
                  `}
                  title="Downvote"
                >
                  <ThumbsDown size={12} className={userVote === VOTE_TYPES.DOWNVOTE ? 'fill-current' : ''} />
                  <span>{voteCount.down}</span>
                </button>
              </>
            )}

            {voteError && (
              <p className="text-xs text-amber-600 mt-1 text-center">{voteError}</p>
            )}
          </div>
        </div>
      </div>
    </Link>
  );
}
