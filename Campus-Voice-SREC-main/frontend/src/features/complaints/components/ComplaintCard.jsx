import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import complaintService from '../../../services/complaint.service';
import {
  ThumbsUp, ThumbsDown, FileX, ShieldCheck,
  Clock, Building2, AlertCircle
} from 'lucide-react';
import { Skeleton } from '../../../components/UI';
import { VOTE_TYPES } from '../../../utils/constants';

// Status config: color + label
const STATUS_CFG = {
  Raised:      { dot: 'bg-blue-400',   text: 'text-blue-600',   label: 'Raised' },
  'In Progress':{ dot: 'bg-amber-400',  text: 'text-amber-600',  label: 'In Progress' },
  Resolved:    { dot: 'bg-green-500',  text: 'text-green-700',  label: 'Resolved' },
  Closed:      { dot: 'bg-gray-400',   text: 'text-gray-500',   label: 'Closed' },
  Spam:        { dot: 'bg-red-400',    text: 'text-red-600',    label: 'Spam' },
};

// Priority config
const PRIORITY_CFG = {
  Critical: { bar: 'bg-red-500',    label: 'Critical', text: 'text-red-600' },
  High:     { bar: 'bg-orange-400', label: 'High',     text: 'text-orange-600' },
  Medium:   { bar: 'bg-amber-400',  label: 'Medium',   text: 'text-amber-600' },
  Low:      { bar: 'bg-gray-300',   label: 'Low',      text: 'text-gray-400' },
};

// Category background accent
const CATEGORY_COLOR = {
  'Men\'s Hostel':    'bg-blue-50 text-blue-700 border-blue-100',
  'Women\'s Hostel':  'bg-pink-50 text-pink-700 border-pink-100',
  'General':          'bg-gray-50 text-gray-600 border-gray-200',
  'Department':       'bg-violet-50 text-violet-700 border-violet-100',
  'Disciplinary Committee': 'bg-red-50 text-red-700 border-red-100',
};

const timeAgo = (ts) => {
  if (!ts) return '';
  const diff = Date.now() - new Date(ts).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${d}d`;
  return new Date(ts).toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
};

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
  const [voteCount, setVoteCount] = useState({ up: upvotes || 0, down: downvotes || 0 });
  const [userVote, setUserVote] = useState(null);
  const [isVoting, setIsVoting] = useState(false);
  const [voteError, setVoteError] = useState(null);
  const [imageUrl, setImageUrl] = useState(null);
  const [imageLoading, setImageLoading] = useState(false);

  const showVoteError = (msg) => {
    setVoteError(msg);
    setTimeout(() => setVoteError(null), 3000);
  };

  useEffect(() => {
    if (isOwner) return;
    const fetchMyVote = async () => {
      try {
        const v = await complaintService.getMyVote(id);
        setUserVote(v.has_voted ? v.vote_type : null);
      } catch {}
    };
    const t = setTimeout(fetchMyVote, Math.random() * 500);
    return () => clearTimeout(t);
  }, [id, isOwner]);

  useEffect(() => {
    let active = true;
    if (!has_image) { setImageUrl(null); return; }
    setImageLoading(true);
    const t = setTimeout(() => {
      complaintService.fetchImage(id, true)
        .then(url => { if (active) setImageUrl(url); })
        .catch(() => { if (active) setImageUrl(null); })
        .finally(() => { if (active) setImageLoading(false); });
    }, Math.random() * 800);
    return () => {
      clearTimeout(t);
      active = false;
      if (imageUrl) URL.revokeObjectURL(imageUrl);
    };
  }, [id, has_image]);

  useEffect(() => {
    setVoteCount({ up: upvotes || 0, down: downvotes || 0 });
  }, [upvotes, downvotes]);

  const handleVote = async (e, type) => {
    e.preventDefault();
    if (!user?.roll_no) { showVoteError("Login to vote"); return; }
    if (isVoting) return;
    setIsVoting(true);

    const prevVote = userVote;
    const prevCount = { ...voteCount };
    const isRemoving = userVote === type;

    let newUp = voteCount.up, newDown = voteCount.down;
    if (isRemoving) {
      if (type === VOTE_TYPES.UPVOTE) newUp--; else newDown--;
      setUserVote(null);
    } else {
      if (prevVote === VOTE_TYPES.UPVOTE) newUp--;
      if (prevVote === VOTE_TYPES.DOWNVOTE) newDown--;
      if (type === VOTE_TYPES.UPVOTE) newUp++; else newDown++;
      setUserVote(type);
    }
    setVoteCount({ up: Math.max(0, newUp), down: Math.max(0, newDown) });

    try {
      const res = isRemoving
        ? await complaintService.removeVote(id)
        : await complaintService.voteOnComplaint(id, type);
      setVoteCount({ up: res.upvotes, down: res.downvotes });
      setUserVote(res.user_vote);
    } catch (err) {
      setVoteCount(prevCount);
      setUserVote(prevVote);
      const msg = (err?.response?.data?.error || err?.response?.data?.detail || err.message || '').toLowerCase();
      if (msg.includes('own') || msg.includes('cannot vote') || err?.response?.status === 403)
        showVoteError("Can't vote on your own complaint");
      else showVoteError("Vote failed. Try again.");
    } finally {
      setIsVoting(false);
    }
  };

  const bodyText = isOwner
    ? (desc || summary || '')
    : (rephrased_text || summary || desc || '');

  const sc = STATUS_CFG[status] || STATUS_CFG['Raised'];
  const pc = PRIORITY_CFG[priority] || PRIORITY_CFG['Low'];
  const catColor = CATEGORY_COLOR[category] || 'bg-gray-50 text-gray-600 border-gray-200';

  return (
    <Link to={`/complaint/${id}`} className="block group">
      <div className={`bg-white rounded-xl border border-gray-100 overflow-hidden shadow-sm group-hover:shadow-md group-hover:-translate-y-0.5 transition-all duration-200 ${priority === 'Critical' ? 'border-t-2 border-t-red-400' : ''}`}>

        {/* Priority accent bar (top) */}
        <div className={`h-0.5 w-full ${pc.bar}`} />

        <div className="p-3">
          {/* Row 1: category tag + status pill + timestamp */}
          <div className="flex items-center gap-1.5 mb-2 flex-wrap">
            {category && (
              <span className={`inline-flex items-center px-1.5 py-0.5 rounded-md text-[10px] font-semibold border ${catColor}`}>
                {category}
              </span>
            )}
            <span className={`inline-flex items-center gap-1 text-[10px] font-medium ${sc.text}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${sc.dot} inline-block`} />
              {sc.label}
            </span>
            {priority && priority !== 'Low' && (
              <span className={`text-[10px] font-semibold ${pc.text}`}>· {pc.label}</span>
            )}
            <span className="text-[10px] text-gray-300 ml-auto flex items-center gap-0.5">
              <Clock size={9} />
              {timeAgo(timestamp)}
            </span>
          </div>

          {/* Row 2: content + image thumbnail side by side */}
          <div className="flex gap-2.5 items-start">
            {/* Text content */}
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-700 leading-snug line-clamp-2">
                {bodyText}
              </p>

              {/* Assigned authority (owner only) */}
              {isOwner && assigned_authority_name && (
                <div className="flex items-center gap-1 mt-1.5">
                  <ShieldCheck size={10} className="text-green-500 flex-shrink-0" />
                  <span className="text-[10px] text-gray-500 truncate">{assigned_authority_name}</span>
                </div>
              )}

              {/* Department code (if present) */}
              {department_code && !isOwner && (
                <div className="flex items-center gap-1 mt-1">
                  <Building2 size={10} className="text-gray-300 flex-shrink-0" />
                  <span className="text-[10px] text-gray-400">{department_code}</span>
                </div>
              )}
            </div>

            {/* Thumbnail */}
            {has_image && (
              <div className="w-16 h-16 flex-shrink-0 rounded-lg overflow-hidden bg-gray-100">
                {imageLoading ? (
                  <Skeleton className="w-full h-full" />
                ) : imageUrl ? (
                  <img src={imageUrl} alt="" className="w-full h-full object-cover" />
                ) : (
                  <div className="flex items-center justify-center h-full text-gray-200">
                    <FileX size={16} strokeWidth={1.5} />
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Row 3: vote buttons (always full-width below content) */}
          <div className="flex items-center mt-2.5 pt-2 border-t border-gray-50">
            {!isOwner ? (
              <div className="flex items-center gap-1.5 ml-auto" onClick={e => { e.preventDefault(); e.stopPropagation(); }}>
                <button
                  onClick={e => handleVote(e, VOTE_TYPES.UPVOTE)}
                  disabled={isVoting}
                  className={`flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold transition-all active:scale-95 ${
                    userVote === VOTE_TYPES.UPVOTE
                      ? 'bg-srec-primary text-white shadow-sm'
                      : 'bg-gray-50 text-gray-400 border border-gray-200 hover:border-srec-primary/40 hover:text-srec-primary hover:bg-srec-primary/5'
                  }`}
                >
                  <ThumbsUp size={11} className={userVote === VOTE_TYPES.UPVOTE ? 'fill-current' : ''} />
                  <span>{voteCount.up}</span>
                </button>
                <button
                  onClick={e => handleVote(e, VOTE_TYPES.DOWNVOTE)}
                  disabled={isVoting}
                  className={`flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold transition-all active:scale-95 ${
                    userVote === VOTE_TYPES.DOWNVOTE
                      ? 'bg-srec-danger text-white shadow-sm'
                      : 'bg-gray-50 text-gray-400 border border-gray-200 hover:border-red-300 hover:text-srec-danger hover:bg-red-50'
                  }`}
                >
                  <ThumbsDown size={11} className={userVote === VOTE_TYPES.DOWNVOTE ? 'fill-current' : ''} />
                  <span>{voteCount.down}</span>
                </button>
              </div>
            ) : (
              <span className="text-[10px] text-gray-300 ml-auto italic">Your complaint</span>
            )}
          </div>

          {voteError && (
            <div className="flex items-center gap-1 mt-1.5 text-[10px] text-red-500">
              <AlertCircle size={10} />
              {voteError}
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}
