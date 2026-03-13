import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import complaintService from '../../../services/complaint.service';
import {
  ThumbsUp, ThumbsDown, FileX, ShieldCheck,
  Clock, Building2, AlertCircle, Copy, Check, ImagePlus
} from 'lucide-react';
import { Skeleton } from '../../../components/UI';
import { VOTE_TYPES } from '../../../utils/constants';

// Status config: dot color, label, badge style
const STATUS_CFG = {
  Raised:        { dot: 'bg-blue-400',    badge: 'bg-blue-50 text-blue-700 border border-blue-100',   label: 'Raised' },
  'In Progress': { dot: 'bg-amber-400',   badge: 'bg-amber-50 text-amber-700 border border-amber-100', label: 'In Progress' },
  Resolved:      { dot: 'bg-emerald-500', badge: 'bg-emerald-50 text-emerald-700 border border-emerald-100', label: 'Resolved' },
  Closed:        { dot: 'bg-gray-400',    badge: 'bg-gray-100 text-gray-500 border border-gray-200',   label: 'Closed' },
  Spam:          { dot: 'bg-red-400',     badge: 'bg-red-50 text-red-700 border border-red-100',       label: 'Spam' },
};

// Priority config — gradient bar + label + accent color
const PRIORITY_CFG = {
  Critical: { bar: 'from-red-500 to-rose-400',     label: 'Critical', accent: 'text-red-600',    pill: 'bg-red-50 text-red-700 border border-red-100' },
  High:     { bar: 'from-orange-500 to-amber-400', label: 'High',     accent: 'text-orange-600', pill: 'bg-orange-50 text-orange-700 border border-orange-100' },
  Medium:   { bar: 'from-amber-400 to-yellow-300', label: 'Medium',   accent: 'text-amber-600',  pill: 'bg-amber-50 text-amber-700 border border-amber-100' },
  Low:      { bar: 'from-gray-300 to-gray-200',    label: 'Low',      accent: 'text-gray-400',   pill: 'bg-gray-50 text-gray-500 border border-gray-200' },
};

// Category chip colors — richer green palette for hostel
const CATEGORY_COLOR = {
  "Men's Hostel":          'bg-emerald-50 text-emerald-800 border border-emerald-200',
  "Women's Hostel":        'bg-pink-50 text-pink-800 border border-pink-200',
  'General':               'bg-slate-50 text-slate-700 border border-slate-200',
  'Department':            'bg-violet-50 text-violet-800 border border-violet-200',
  'Disciplinary Committee':'bg-rose-50 text-rose-800 border border-rose-200',
};

const timeAgo = (ts) => {
  if (!ts) return '';
  const diff = Date.now() - new Date(ts).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d === 1) return 'Yesterday';
  if (d < 7) return `${d}d ago`;
  return new Date(ts).toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
};

export default function ComplaintCard({
  id,
  desc,
  summary,
  rephrased_text,
  category,
  department_code,
  status,
  priority,
  upvotes,
  downvotes,
  timestamp,
  isOwner = false,
  has_image = false,
  assigned_authority_name = null,
  image_required = false,
  image_pending = false,
  image_required_deadline = null,
}) {
  const { user } = useAuth();
  const [voteCount, setVoteCount] = useState({ up: upvotes || 0, down: downvotes || 0 });
  const [userVote, setUserVote] = useState(null);
  const [isVoting, setIsVoting] = useState(false);
  const [voteError, setVoteError] = useState(null);
  const [imageUrl, setImageUrl] = useState(null);
  const [imageLoading, setImageLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [imageUploaded, setImageUploaded] = useState(false);
  const imgInputRef = useRef(null);

  const copyId = async (e, complaintId) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(complaintId);
    } catch {
      const el = document.createElement('textarea');
      el.value = complaintId;
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const showVoteError = (msg) => {
    setVoteError(msg);
    setTimeout(() => setVoteError(null), 3000);
  };

  const handleImageUpload = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingImage(true);
    try {
      await complaintService.uploadImage(id, file);
      setImageUploaded(true);
    } catch (err) {
      console.error('Image upload failed', err);
    } finally {
      setUploadingImage(false);
      if (imgInputRef.current) imgInputRef.current.value = '';
    }
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
      // api.js sets err.status and err.data (not err.response)
      const errData = err?.data || {};
      const errDetail = errData?.detail;
      const errMsg = errData?.error
        || (typeof errDetail === 'string' ? errDetail : errDetail?.error)
        || err.message || '';
      const errLower = errMsg.toLowerCase();
      if (err?.status === 403 || errLower.includes('own') || errLower.includes('cannot vote')) {
        showVoteError("Can't vote on your own complaint");
      } else if (errLower.includes('already')) {
        showVoteError("You've already voted this way.");
      } else if (errLower.includes('resolved')) {
        showVoteError("Voting closed for resolved complaints.");
      } else {
        showVoteError("Vote failed. Try again.");
      }
    } finally {
      setIsVoting(false);
    }
  };

  const bodyText = isOwner
    ? (desc || summary || '')
    : (rephrased_text || summary || desc || '');

  const sc = STATUS_CFG[status] || STATUS_CFG['Raised'];
  const pc = PRIORITY_CFG[priority] || PRIORITY_CFG['Low'];
  const catColor = CATEGORY_COLOR[category] || 'bg-slate-50 text-slate-700 border border-slate-200';

  return (
    <Link to={`/complaint/${id}`} className="block group">
      <div className="bg-white rounded-xl border border-srec-border overflow-hidden shadow-card group-hover:shadow-card-hover group-hover:-translate-y-0.5 transition-all duration-300">

        {/* Priority gradient accent bar */}
        <div className={`h-[2px] w-full bg-gradient-to-r opacity-80 ${pc.bar}`} />

        <div className="p-3.5">
          {/* Row 1: category tag + status badge + timestamp */}
          <div className="flex items-center gap-1.5 mb-2.5 flex-wrap">
            {category && (
              <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-semibold ${catColor}`}>
                {category}
              </span>
            )}
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${sc.badge}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${sc.dot} inline-block`} />
              {sc.label}
            </span>
            {priority && priority !== 'Low' && (
              <span className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-semibold ${pc.pill}`}>
                {pc.label}
              </span>
            )}
            <span className="text-[10px] text-srec-textMuted ml-auto flex items-center gap-0.5 flex-shrink-0">
              <Clock size={9} />
              {timeAgo(timestamp)}
            </span>
          </div>

          {/* Row 2: content + image thumbnail side by side */}
          <div className="flex gap-2.5 items-start">
            {/* Text content */}
            <div className="flex-1 min-w-0">
              <p className="text-sm text-srec-textSecondary leading-snug line-clamp-2">
                {bodyText}
              </p>

              {/* Assigned authority — visible to all */}
              {assigned_authority_name && (
                <div className="flex items-center gap-1 mt-1.5">
                  <ShieldCheck size={10} className="text-srec-primary flex-shrink-0" />
                  <span className="text-[10px] text-srec-primary font-medium truncate">
                    {assigned_authority_name}
                  </span>
                </div>
              )}

              {/* Department code (if present and no authority shown) */}
              {department_code && !assigned_authority_name && !isOwner && (
                <div className="flex items-center gap-1 mt-1">
                  <Building2 size={10} className="text-srec-textMuted flex-shrink-0" />
                  <span className="text-[10px] text-srec-textMuted">{department_code}</span>
                </div>
              )}
            </div>

            {/* Thumbnail */}
            {has_image && (
              <div className="w-16 h-16 flex-shrink-0 rounded-lg overflow-hidden bg-srec-backgroundAlt ring-1 ring-srec-border">
                {imageLoading ? (
                  <Skeleton className="w-full h-full" />
                ) : imageUrl ? (
                  <img src={imageUrl} alt="" className="w-full h-full object-cover" />
                ) : (
                  <div className="flex items-center justify-center h-full text-srec-textMuted">
                    <FileX size={16} strokeWidth={1.5} />
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Image upload prompt — shown to owner when image is required and not yet uploaded */}
          {isOwner && image_required && image_pending && !has_image && !imageUploaded && (
            <div
              className="mt-2.5 flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2"
              onClick={e => e.preventDefault()}
            >
              <ImagePlus size={13} className="text-amber-600 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-[10px] font-semibold text-amber-800 leading-none">Image required</p>
                {image_required_deadline && (
                  <p className="text-[9px] text-amber-600 mt-0.5">
                    Due by {new Date(image_required_deadline).toLocaleDateString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                  </p>
                )}
              </div>
              <label
                onClick={e => e.stopPropagation()}
                className={`flex-shrink-0 flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-semibold cursor-pointer transition-colors ${
                  uploadingImage ? 'bg-amber-200 text-amber-600' : 'bg-amber-500 text-white hover:bg-amber-600'
                }`}
              >
                {uploadingImage ? 'Uploading…' : 'Upload'}
                <input
                  ref={imgInputRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={handleImageUpload}
                  disabled={uploadingImage}
                />
              </label>
            </div>
          )}
          {isOwner && image_required && image_pending && imageUploaded && (
            <div className="mt-2.5 flex items-center gap-2 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">
              <Check size={13} className="text-emerald-600 flex-shrink-0" />
              <p className="text-[10px] font-semibold text-emerald-700">Image uploaded — awaiting verification</p>
            </div>
          )}

          {/* Row 3: copy ID + vote buttons */}
          <div className="flex items-center mt-3 pt-2.5 border-t border-srec-borderLight">
            {/* Copy ID button — always visible, stops link navigation */}
            <button
              onClick={(e) => copyId(e, id)}
              className="flex items-center gap-1 text-[10px] text-srec-textMuted hover:text-srec-primary transition-colors"
              title="Copy complaint ID"
            >
              {copied ? (
                <><Check size={11} className="text-green-500" /><span className="text-green-500">Copied!</span></>
              ) : (
                <><Copy size={11} /><span className="font-mono">#{id?.toString().slice(-6).toUpperCase()}</span></>
              )}
            </button>

            {!isOwner ? (
              <div className="flex items-center gap-1.5 ml-auto" onClick={e => { e.preventDefault(); e.stopPropagation(); }}>
                <button
                  onClick={e => handleVote(e, VOTE_TYPES.UPVOTE)}
                  disabled={isVoting}
                  className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[11px] font-semibold transition-all duration-150 active:scale-95 will-change-transform ${
                    userVote === VOTE_TYPES.UPVOTE
                      ? 'bg-srec-primary text-white shadow-sm ring-1 ring-srec-primary/20'
                      : 'bg-srec-backgroundAlt text-srec-textMuted border border-srec-border hover:border-srec-primaryMuted hover:text-srec-primary hover:bg-srec-primarySoft'
                  }`}
                >
                  <ThumbsUp size={11} className={userVote === VOTE_TYPES.UPVOTE ? 'fill-current' : ''} />
                  <span>{voteCount.up}</span>
                </button>
                <button
                  onClick={e => handleVote(e, VOTE_TYPES.DOWNVOTE)}
                  disabled={isVoting}
                  className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[11px] font-semibold transition-all duration-150 active:scale-95 will-change-transform ${
                    userVote === VOTE_TYPES.DOWNVOTE
                      ? 'bg-rose-500 text-white shadow-sm ring-1 ring-rose-200'
                      : 'bg-srec-backgroundAlt text-srec-textMuted border border-srec-border hover:border-rose-300 hover:text-rose-600 hover:bg-rose-50'
                  }`}
                >
                  <ThumbsDown size={11} className={userVote === VOTE_TYPES.DOWNVOTE ? 'fill-current' : ''} />
                  <span>{voteCount.down}</span>
                </button>
              </div>
            ) : (
              <span className="text-[10px] text-srec-textMuted ml-auto italic">Your complaint</span>
            )}
          </div>

          {voteError && (
            <div className="flex items-center gap-1 mt-1.5 text-[10px] text-rose-500">
              <AlertCircle size={10} />
              {voteError}
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}
