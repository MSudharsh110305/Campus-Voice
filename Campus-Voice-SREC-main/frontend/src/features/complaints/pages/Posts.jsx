import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { TopNav } from '../../../components/Navbars';
import BottomNav from '../../../components/BottomNav';
import { Card, Button, EliteButton } from '../../../components/UI';
import ComplaintCard from '../components/ComplaintCard';
import { useAuth } from '../../../context/AuthContext';
import complaintService from '../../../services/complaint.service';
import studentService from '../../../services/student.service';
import { Upload, X, FileX, Inbox, AlertTriangle, ThumbsUp, Search, SlidersHorizontal, Camera, Image, WifiOff, Copy, Check, Trash2 } from 'lucide-react';
import { VISIBILITY, COMPLAINT_CATEGORIES, STATUSES, PRIORITIES } from '../../../utils/constants';

export default function Posts() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  // Restore tab from URL so pressing back from complaint detail returns to the correct tab
  const [activeTab, setActiveTab] = useState(() => {
    const t = searchParams.get('tab');
    return t === 'mine' || t === 'feed' ? t : 'create';
  });

  const switchTab = (tab) => {
    setActiveTab(tab);
    if (tab === 'create') {
      setSearchParams({});
    } else {
      // Preserve existing filter params when switching tabs
      const next = { tab };
      const s = searchParams.get('status'); if (s && s !== 'All') next.status = s;
      const p = searchParams.get('priority'); if (p && p !== 'All') next.priority = p;
      setSearchParams(next);
    }
  };

  // Camera / gallery refs for mobile PWA feature
  const cameraRef = useRef(null);
  const galleryRef = useRef(null);
  const isMobile = /Android|iPhone|iPad/i.test(navigator.userAgent);

  const [formData, setFormData] = useState(() => {
    try {
      const draft = localStorage.getItem('cv_complaint_draft');
      if (draft) return { original_text: draft, image: null, visibility: 'Public' };
    } catch {}
    return { original_text: '', image: null, visibility: 'Public' };
  });
  const [imagePreview, setImagePreview] = useState(null);
  const [myPosts, setMyPosts] = useState([]);
  const [submitted, setSubmitted] = useState(false);
  const [apiResponse, setApiResponse] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState('');
  const [idCopied, setIdCopied] = useState(false);

  // My Posts filters — status/priority persisted in URL so back navigation restores them
  const [mineFilters, setMineFilters] = useState(() => ({
    status: searchParams.get('status') || 'All',
    priority: searchParams.get('priority') || 'All',
    search: '',
  }));

  const updateMineFilter = (key, value) => {
    setMineFilters(f => {
      const next = { ...f, [key]: value };
      // Sync status/priority to URL (search stays local)
      const params = { tab: 'mine' };
      if (next.status !== 'All') params.status = next.status;
      if (next.priority !== 'All') params.priority = next.priority;
      setSearchParams(params, { replace: true });
      return next;
    });
  };

  const clearMineFilters = () => {
    setMineFilters({ status: 'All', priority: 'All', search: '' });
    setSearchParams({ tab: 'mine' }, { replace: true });
  };

  // Duplicate-check modal state
  const [dupModalOpen, setDupModalOpen] = useState(false);
  const [dupCandidates, setDupCandidates] = useState([]);
  const [isDupChecking, setIsDupChecking] = useState(false);
  // Track votes cast in the dup modal: { [complaintId]: 'upvoted' | 'error' }
  const [dupVotes, setDupVotes] = useState({});

  // Delete confirmation: null | complaintId
  const [deleteConfirmId, setDeleteConfirmId] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDeleteComplaint = async (id) => {
    setIsDeleting(true);
    try {
      await complaintService.deleteComplaint(id);
      setMyPosts(prev => prev.filter(p => (p.id || p.complaint_id) !== id));
    } catch (err) {
      console.error('Delete failed:', err);
    } finally {
      setIsDeleting(false);
      setDeleteConfirmId(null);
    }
  };

  const copyComplaintId = async (id) => {
    try {
      await navigator.clipboard.writeText(id);
    } catch {
      const el = document.createElement('input');
      el.value = id;
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
    }
    setIdCopied(true);
    setTimeout(() => setIdCopied(false), 2000);
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    const newVal = type === 'checkbox' ? checked : value;
    setFormData({ ...formData, [name]: newVal });
    if (name === 'original_text') {
      try { newVal ? localStorage.setItem('cv_complaint_draft', newVal) : localStorage.removeItem('cv_complaint_draft'); } catch {}
    }
  };

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        setFormError('Image must be less than 5MB');
        return;
      }
      const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
      if (!allowedTypes.includes(file.type)) {
        setFormError('Only JPEG, PNG, GIF, and WebP images are allowed');
        return;
      }
      setFormError('');
      setFormData({ ...formData, image: file });
      setImagePreview(URL.createObjectURL(file));
    }
  };

  useEffect(() => {
    const fetchMyComplaints = async () => {
      if (activeTab === 'mine') {
        try {
          const response = await studentService.getMyComplaints({ skip: 0, limit: 50 });
          if (Array.isArray(response)) {
            setMyPosts(response);
          } else if (response && Array.isArray(response.complaints)) {
            setMyPosts(response.complaints);
          } else if (response && Array.isArray(response.data)) {
            setMyPosts(response.data);
          } else {
            setMyPosts([]);
          }
        } catch (error) {
          console.error("Failed to fetch complaints:", error);
          setMyPosts([]);
        }
      }
    };

    fetchMyComplaints();
    // Auto-refresh every 30s so new complaints/status changes appear without manual reload
    const interval = setInterval(fetchMyComplaints, 30000);
    return () => clearInterval(interval);
  }, [activeTab]);

  // Called when user clicks "Submit" — first checks for duplicates
  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');

    if (!formData.original_text || formData.original_text.trim().length < 10) {
      setFormError('Complaint text must be at least 10 characters.');
      return;
    }

    if (formData.original_text.length > 2000) {
      setFormError('Complaint text must not exceed 2000 characters.');
      return;
    }

    const textWithoutSpaces = formData.original_text.replace(/\s/g, '');
    if (textWithoutSpaces === textWithoutSpaces.toUpperCase() && /[A-Z]/.test(textWithoutSpaces)) {
      setFormError('Please avoid writing in ALL CAPS.');
      return;
    }

    // Duplicate check before submitting
    try {
      setIsDupChecking(true);
      const dupResult = await complaintService.checkDuplicate(formData.original_text);
      if (dupResult?.is_likely_duplicate && dupResult?.duplicates?.length > 0) {
        setDupCandidates(dupResult.duplicates);
        setDupModalOpen(true);
        return; // stop — let user decide in modal
      }
    } catch (_) {
      // Silently ignore — don't block submission if check fails
    } finally {
      setIsDupChecking(false);
    }

    await doSubmit();
  };

  // Vote on a duplicate complaint directly from the modal
  const handleDupUpvote = async (complaintId) => {
    if (dupVotes[complaintId]) return; // already voted
    try {
      await complaintService.voteOnComplaint(complaintId, 'Upvote');
      setDupVotes(prev => ({ ...prev, [complaintId]: 'upvoted' }));
      setDupCandidates(prev =>
        prev.map(c => c.id === complaintId ? { ...c, upvotes: (c.upvotes || 0) + 1 } : c)
      );
    } catch (_) {
      setDupVotes(prev => ({ ...prev, [complaintId]: 'error' }));
    }
  };

  // The actual API submission (called directly or after user confirms from modal)
  const doSubmit = async () => {
    setIsSubmitting(true);
    setDupModalOpen(false);
    setFormError('');

    // Feature 2: Offline draft — save to IndexedDB and register background sync
    if (!navigator.onLine) {
      try {
        const { queueComplaint } = await import('../../../utils/idb.js');
        const { tokenStorage } = await import('../../../utils/api.js');
        await queueComplaint({
          original_text: formData.original_text,
          visibility: formData.visibility,
          is_anonymous: true,
          access_token: tokenStorage.getAccessToken(),
        });
        if ('serviceWorker' in navigator && 'SyncManager' in window) {
          const reg = await navigator.serviceWorker.ready;
          await reg.sync.register('submit-complaint').catch(() => {});
        }
      } catch (_) {
        // Silently ignore IDB/SW errors — still show offline success
      }
      setApiResponse({ offline: true });
      setSubmitted(true);
      setIsSubmitting(false);
      return;
    }

    try {
      const fd = new FormData();
      fd.append('original_text', formData.original_text);
      fd.append('visibility', formData.visibility);
      fd.append('is_anonymous', 'true');
      if (formData.image) {
        fd.append('image', formData.image);
      }

      const response = await complaintService.submitComplaint(fd);

      setApiResponse(response);
      setSubmitted(true);

      // Feature 6: trigger install prompt once after first successful submission
      const alreadyInstalled = window.matchMedia('(display-mode: standalone)').matches;
      const alreadyPrompted = localStorage.getItem('cv_install_prompted');
      if (!alreadyInstalled && !alreadyPrompted) {
        localStorage.setItem('cv_install_prompted', '1');
        window.dispatchEvent(new CustomEvent('cv:show-install-prompt'));
      }

      const newPost = {
        id: response.id || Date.now(),
        submitted_at: new Date().toISOString(),
        status: response.status || 'Pending',
        category: response.category,
        priority: response.priority,
        upvotes: 0,
        ...response
      };
      setMyPosts([newPost, ...myPosts]);

      setFormData({ original_text: '', image: null, visibility: 'Public' });
      try { localStorage.removeItem('cv_complaint_draft'); } catch {}
      setImagePreview(null);
      setDupCandidates([]);

    } catch (error) {
      console.error(error);
      setFormError(error.message || 'Failed to submit complaint');
    } finally {
      setIsSubmitting(false);
    }
  };

  const inputClass = "w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-900 placeholder:text-gray-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary transition-all resize-none";

  // Success screen
  if (submitted && apiResponse) {
    // Offline draft saved state
    if (apiResponse.offline) {
      return (
        <div className="fixed inset-0 z-50 min-h-screen bg-srec-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="max-w-lg w-full mx-auto p-8 bg-white rounded-2xl shadow-xl border border-white/60 text-center">
            <div className="mb-5 flex justify-center">
              <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center shadow-inner">
                <WifiOff size={36} className="text-gray-400" />
              </div>
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">Saved for later</h3>
            <p className="text-sm text-gray-500 mt-1 max-w-xs mx-auto">
              Your complaint is saved and will auto-submit when you're back online.
            </p>
            <button
              onClick={() => { setSubmitted(false); setApiResponse(null); }}
              className="mt-7 w-full py-3 bg-srec-primary text-white font-semibold rounded-xl hover:bg-srec-primaryHover transition-all duration-200 shadow-sm"
            >
              Back to form
            </button>
          </div>
        </div>
      );
    }

    return (
      <div className="fixed inset-0 z-50 min-h-screen bg-srec-background/80 backdrop-blur-sm flex items-center justify-center p-4">
        <div className="max-w-lg w-full mx-auto p-8 bg-white rounded-2xl shadow-xl overflow-y-auto max-h-[90vh] border border-white/60">
          <div className="mb-6 flex justify-center">
            <div className="w-20 h-20 bg-srec-primary/10 rounded-full flex items-center justify-center shadow-inner">
              <svg className="w-10 h-10 text-srec-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>

          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Complaint Submitted!</h2>
            <p className="text-gray-500">AI has analyzed your complaint.</p>
          </div>

          <div className="space-y-4 bg-gray-50 p-6 rounded-xl border border-gray-100 mb-8">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-xs text-gray-400 uppercase tracking-wide font-bold">Status</span>
                <p className="font-semibold text-gray-900">{apiResponse.status || 'Pending'}</p>
              </div>
              <div>
                <span className="text-xs text-gray-400 uppercase tracking-wide font-bold">Category</span>
                <p className="font-medium text-srec-primary">{COMPLAINT_CATEGORIES[apiResponse.category_id] || 'AI Analysis Pending'}</p>
              </div>
              <div>
                <span className="text-xs text-gray-400 uppercase tracking-wide font-bold">Priority</span>
                <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold mt-1
                     ${apiResponse.priority === 'High' ? 'bg-red-50 text-error' : 'bg-green-50 text-srec-primary'}`}>
                  {apiResponse.priority || 'Normal'}
                </span>
              </div>
              <div>
                <span className="text-xs text-gray-400 uppercase tracking-wide font-bold">Assigned To</span>
                <p className="font-medium text-gray-900">{apiResponse.assigned_authority_name || 'Pending Assignment'}</p>
              </div>
              {apiResponse.target_department_code && (
                <div>
                  <span className="text-xs text-gray-400 uppercase tracking-wide font-bold">Department</span>
                  <p className="font-medium text-gray-900">{apiResponse.target_department_code}</p>
                </div>
              )}
              {apiResponse.cross_department && (
                <div>
                  <span className="text-xs text-gray-400 uppercase tracking-wide font-bold">Routing</span>
                  <p className="font-medium text-orange-600">Cross-Department</p>
                </div>
              )}
            </div>

            {apiResponse.id && (
              <div className="pt-4 border-t border-gray-200 flex items-center justify-between">
                <div>
                  <span className="text-xs text-gray-400 uppercase tracking-wide font-bold">Complaint ID</span>
                  <p className="font-mono text-xs text-gray-600 mt-0.5">#{apiResponse.id.toString().slice(-8).toUpperCase()}</p>
                </div>
                <button
                  onClick={() => copyComplaintId(apiResponse.id)}
                  className="inline-flex items-center gap-1 text-xs text-srec-primary hover:underline"
                >
                  {idCopied ? <><Check size={11} /> Copied!</> : <><Copy size={11} /> Copy ID</>}
                </button>
              </div>
            )}

            <div className="pt-4 border-t border-gray-200">
              <span className="text-xs text-gray-400 uppercase tracking-wide font-bold">AI Rephrased Complaint</span>
              <p className="text-sm text-gray-700 mt-1 italic leading-relaxed">"{apiResponse.rephrased_text || apiResponse.summary || 'Processing...'}"</p>
            </div>

            {apiResponse.has_image && apiResponse.image_verification_status && (
              <div className="pt-4 border-t border-gray-200">
                <span className="text-xs text-gray-400 uppercase tracking-wide font-bold">Image Verification</span>
                <p className={`text-sm mt-1 ${apiResponse.image_verified ? 'text-green-600' : 'text-orange-600'}`}>
                  {(() => {
                    const msg = apiResponse.image_verification_message;
                    if (!msg) return apiResponse.image_verification_status;
                    try {
                      const stripped = msg.replace(/```json\s*/g, '').replace(/```/g, '').trim();
                      const parsed = JSON.parse(stripped);
                      return parsed.reason || parsed.explanation || apiResponse.image_verification_status;
                    } catch {
                      return msg;
                    }
                  })()}
                </p>
              </div>
            )}

            {apiResponse.llm_failed && (
              <div className="pt-4 border-t border-gray-200 bg-yellow-50 -mx-6 -mb-6 px-6 py-4 rounded-b-xl">
                <p className="text-xs text-yellow-700">
                  AI analysis is temporarily unavailable. Your complaint has been submitted and will be manually reviewed.
                </p>
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Button
              variant="secondary"
              onClick={() => {
                setSubmitted(false);
                setApiResponse(null);
                switchTab('mine');
              }}
              className="py-3"
            >
              View My Posts
            </Button>
            <Button
              variant="primary"
              onClick={() => {
                setSubmitted(false);
                setApiResponse(null);
                navigate('/home');
              }}
              className="py-3"
            >
              Go to Home
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-srec-background">
      <TopNav />

      <div className="animate-fadeIn max-w-3xl mx-auto px-4 pt-4 pb-24 md:pl-24 transition-all duration-300">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-xl font-bold text-gray-900 tracking-tight font-heading">Posts</h1>

          {/* Pill tab switcher */}
          <div className="flex bg-srec-backgroundAlt rounded-full p-1 border border-srec-borderLight">
            <button
              onClick={() => switchTab('create')}
              className={`px-4 py-1.5 text-sm font-medium rounded-full transition-all duration-200 ${activeTab === 'create'
                ? 'bg-white shadow-card text-srec-primary font-semibold'
                : 'text-srec-textMuted hover:text-srec-textSecondary'
                }`}
            >
              Create
            </button>
            <button
              onClick={() => switchTab('mine')}
              className={`px-4 py-1.5 text-sm font-medium rounded-full transition-all duration-200 ${activeTab === 'mine'
                ? 'bg-white shadow-card text-srec-primary font-semibold'
                : 'text-srec-textMuted hover:text-srec-textSecondary'
                }`}
            >
              My Posts
            </button>
          </div>
        </div>

        {activeTab === 'create' && (
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-white/60 shadow-[0_4px_24px_-4px_rgba(0,0,0,0.08)] p-5 sm:p-6">
            {formError && (
              <div className="mb-4 bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <textarea
                  name="original_text"
                  value={formData.original_text}
                  onChange={handleChange}
                  placeholder="Describe your complaint in detail (minimum 10 characters)..."
                  rows={5}
                  minLength={10}
                  maxLength={2000}
                  className={inputClass}
                  required
                />
                <p className="text-xs text-gray-400 mt-1 text-right">
                  {formData.original_text.length} / 2000
                </p>
              </div>

              <div>
                <div className="flex gap-3">
                  <label className={`flex-1 flex items-center justify-center gap-2 p-3 rounded-xl border cursor-pointer transition-all duration-200 ${formData.visibility === 'Public' ? 'border-srec-primary bg-srec-primarySoft text-srec-primary shadow-card' : 'border-srec-border bg-white hover:bg-srec-backgroundAlt text-srec-textSecondary'}`}>
                    <input
                      type="radio"
                      name="visibility"
                      value="Public"
                      checked={formData.visibility === 'Public'}
                      onChange={handleChange}
                      className="hidden"
                    />
                    <span className="font-semibold text-sm">Public</span>
                  </label>
                  <label className={`flex-1 flex items-center justify-center gap-2 p-3 rounded-xl border cursor-pointer transition-all duration-200 ${formData.visibility === 'Private' ? 'border-amber-500 bg-amber-50 text-amber-700 shadow-card' : 'border-srec-border bg-white hover:bg-srec-backgroundAlt text-srec-textSecondary'}`}>
                    <input
                      type="radio"
                      name="visibility"
                      value="Private"
                      checked={formData.visibility === 'Private'}
                      onChange={handleChange}
                      className="hidden"
                    />
                    <span className="font-semibold text-sm">Private</span>
                  </label>
                </div>
              </div>

              <div>
                {/* Hidden file inputs — camera (mobile) and gallery */}
                <input
                  ref={cameraRef}
                  type="file"
                  accept="image/*"
                  capture="environment"
                  className="hidden"
                  onChange={handleImageChange}
                />
                <input
                  ref={galleryRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={handleImageChange}
                />

                {!imagePreview ? (
                  isMobile ? (
                    /* Mobile: two distinct tap targets */
                    <div className="flex gap-3">
                      <button
                        type="button"
                        onClick={() => cameraRef.current?.click()}
                        className="flex-1 flex flex-col items-center justify-center gap-1.5 h-24 border-2 border-dashed border-srec-borderHover rounded-xl bg-srec-backgroundAlt hover:bg-srec-primarySoft hover:border-srec-primaryMuted transition-colors duration-200 cursor-pointer"
                      >
                        <Camera className="w-6 h-6 text-srec-textMuted" />
                        <span className="text-xs text-srec-textMuted font-medium">Camera</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => galleryRef.current?.click()}
                        className="flex-1 flex flex-col items-center justify-center gap-1.5 h-24 border-2 border-dashed border-srec-borderHover rounded-xl bg-srec-backgroundAlt hover:bg-srec-primarySoft hover:border-srec-primaryMuted transition-colors duration-200 cursor-pointer"
                      >
                        <Image className="w-6 h-6 text-srec-textMuted" />
                        <span className="text-xs text-srec-textMuted font-medium">Gallery</span>
                      </button>
                    </div>
                  ) : (
                    /* Desktop: single unified button */
                    <button
                      type="button"
                      onClick={() => galleryRef.current?.click()}
                      className="flex flex-col items-center justify-center w-full h-28 border-2 border-dashed border-srec-borderHover rounded-xl cursor-pointer bg-srec-backgroundAlt hover:bg-srec-primarySoft hover:border-srec-primaryMuted transition-colors duration-200"
                    >
                      <Upload className="w-7 h-7 mb-1.5 text-srec-textMuted" />
                      <p className="text-xs text-srec-textMuted font-medium">Click to upload photo (optional, max 5MB)</p>
                    </button>
                  )
                ) : (
                  <div className="relative rounded-xl overflow-hidden border border-gray-200">
                    <img src={imagePreview} alt="Preview" className="w-full h-44 object-cover" />
                    <button
                      type="button"
                      onClick={() => {
                        setFormData({ ...formData, image: null });
                        setImagePreview(null);
                      }}
                      className="absolute top-2 right-2 p-1.5 bg-black/50 text-white rounded-full hover:bg-black/70 transition-colors backdrop-blur-sm"
                    >
                      <X size={15} />
                    </button>
                  </div>
                )}
              </div>

              <button
                type="submit"
                disabled={isSubmitting || isDupChecking}
                className="w-full py-3 bg-srec-primary text-white font-semibold rounded-xl hover:bg-srec-primaryHover transition-all duration-200 shadow-sm disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {isDupChecking ? 'Checking for duplicates…' : isSubmitting ? 'Submitting...' : 'Submit Grievance'}
              </button>
            </form>

            {/* Duplicate warning modal */}
            {dupModalOpen && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-backdrop">
                <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[85vh] overflow-y-auto animate-modal-in">
                  <div className="p-5 border-b border-gray-100 flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0">
                      <AlertTriangle size={18} className="text-amber-600" />
                    </div>
                    <div>
                      <h3 className="font-bold text-gray-900 text-sm">Similar complaints found</h3>
                      <p className="text-xs text-gray-500 mt-0.5">Consider upvoting instead of re-submitting</p>
                    </div>
                  </div>
                  <div className="p-5 space-y-3">
                    {dupCandidates.map((c) => {
                      const voteState = dupVotes[c.id];
                      const voted = voteState === 'upvoted';
                      const isResolved = c.status === 'Resolved' || c.status === 'Closed';
                      const isOwnComplaint = c.is_own;
                      return (
                        <div key={c.id} className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                          <p className="text-xs text-gray-700 line-clamp-3">{c.rephrased_text}</p>
                          <div className="flex items-center gap-2 mt-2 flex-wrap">
                            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${isResolved ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                              {c.status}
                            </span>
                            <span className="text-xs text-gray-500 flex items-center gap-1">
                              <ThumbsUp size={11} /> {c.upvotes}
                            </span>
                            <span className="text-xs text-gray-400">
                              {Math.round(c.similarity_score * 100)}% match
                            </span>
                            <div className="ml-auto">
                              {voted ? (
                                <span className="text-xs text-green-600 font-semibold flex items-center gap-1">
                                  <ThumbsUp size={11} /> Upvoted
                                </span>
                              ) : isResolved || isOwnComplaint ? null : (
                                <button
                                  onClick={() => handleDupUpvote(c.id)}
                                  disabled={!!voteState}
                                  className="text-xs font-semibold px-2.5 py-1 rounded-lg border flex items-center gap-1 transition-colors border-srec-primary/30 text-srec-primary hover:bg-srec-primarySoft disabled:opacity-50"
                                >
                                  <ThumbsUp size={11} />
                                  Upvote
                                </button>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  <div className="p-5 border-t border-gray-100 flex gap-3">
                    <button
                      onClick={() => setDupModalOpen(false)}
                      className="flex-1 py-2.5 rounded-xl border border-gray-200 text-gray-600 text-sm font-medium hover:bg-gray-50 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={doSubmit}
                      className="flex-1 py-2.5 rounded-xl bg-srec-primary text-white text-sm font-semibold hover:bg-srec-primaryDark transition-colors shadow-btn"
                    >
                      Submit anyway
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* My Posts tab */}
        {activeTab === 'mine' && (() => {
          const filteredPosts = (Array.isArray(myPosts) ? myPosts : []).filter(p => {
            if (mineFilters.status !== 'All' && p.status !== mineFilters.status) return false;
            if (mineFilters.priority !== 'All' && p.priority !== mineFilters.priority) return false;
            if (mineFilters.search) {
              const q = mineFilters.search.toLowerCase();
              const text = (p.rephrased_text || p.original_text || '').toLowerCase();
              if (!text.includes(q)) return false;
            }
            return true;
          });

          return (
            <div className="space-y-3">
              {/* Filter bar */}
              {myPosts.length > 0 && (
                <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-white/60 shadow-[0_2px_12px_-2px_rgba(0,0,0,0.06)] p-3 flex flex-wrap gap-2 items-center">
                  <SlidersHorizontal size={14} className="text-gray-400 flex-shrink-0" />
                  <div className="relative flex-1 min-w-[140px]">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" size={12} />
                    <input
                      type="text"
                      placeholder="Search..."
                      value={mineFilters.search}
                      onChange={e => setMineFilters(f => ({ ...f, search: e.target.value }))}
                      className="w-full pl-7 pr-2 py-1.5 text-xs border border-gray-200 rounded-lg focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary outline-none transition-all"
                    />
                  </div>
                  <select
                    value={mineFilters.status}
                    onChange={e => updateMineFilter('status', e.target.value)}
                    className="py-1.5 px-2 text-xs border border-gray-200 rounded-lg focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary outline-none"
                  >
                    <option value="All">All Status</option>
                    {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                  <select
                    value={mineFilters.priority}
                    onChange={e => updateMineFilter('priority', e.target.value)}
                    className="py-1.5 px-2 text-xs border border-gray-200 rounded-lg focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary outline-none"
                  >
                    <option value="All">All Priority</option>
                    {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
                  </select>
                  {(mineFilters.status !== 'All' || mineFilters.priority !== 'All' || mineFilters.search) && (
                    <button
                      onClick={clearMineFilters}
                      className="text-xs text-gray-400 hover:text-srec-danger flex items-center gap-1"
                    >
                      <X size={11} /> Reset
                    </button>
                  )}
                </div>
              )}

              {filteredPosts.length === 0 ? (
                <div className="text-center py-16 bg-white/80 backdrop-blur-sm rounded-2xl border border-white/60 shadow-[0_4px_24px_-4px_rgba(0,0,0,0.08)]">
                  <div className="w-14 h-14 mx-auto mb-3 rounded-full bg-gray-100 flex items-center justify-center">
                    <Inbox size={26} className="text-gray-400" />
                  </div>
                  <p className="text-gray-900 text-base font-semibold">
                    {myPosts.length === 0 ? 'No posts yet' : 'No posts match your filters'}
                  </p>
                  <p className="text-gray-500 text-sm mt-1 max-w-xs mx-auto">
                    {myPosts.length === 0 ? 'Your submitted complaints will appear here' : 'Try adjusting your filters'}
                  </p>
                  {myPosts.length === 0 && (
                    <button
                      className="mt-4 text-sm text-srec-primary font-semibold hover:underline"
                      onClick={() => switchTab('create')}
                    >
                      Raise your first issue
                    </button>
                  )}
                </div>
              ) : (
                filteredPosts.map((post) => {
                  const postId = post.id || post.complaint_id;
                  const isDeletable = !['Resolved', 'Closed'].includes(post.status);
                  return (
                    <div key={postId} className="relative group">
                      <ComplaintCard
                        id={postId}
                        rephrased_text={post.rephrased_text}
                        desc={post.rephrased_text || post.original_text}
                        category={post.category_name || COMPLAINT_CATEGORIES[post.category_id]}
                        has_image={post.has_image}
                        author={post.is_anonymous ? 'Anonymous' : (post.author || post.student_roll_no)}
                        status={post.status}
                        priority={post.priority}
                        upvotes={post.upvotes}
                        timestamp={post.submitted_at || post.created_at}
                        isOwner={true}
                        assigned_authority_name={post.assigned_authority_name || null}
                        image_required={post.image_required || false}
                        image_pending={post.image_pending || false}
                        image_required_deadline={post.image_required_deadline || null}
                      />
                      {isDeletable && deleteConfirmId !== postId && (
                        <button
                          onClick={() => setDeleteConfirmId(postId)}
                          className="absolute top-3 right-3 p-1.5 rounded-lg bg-white/80 text-gray-400 hover:text-srec-danger hover:bg-red-50 border border-gray-200 hover:border-red-200 opacity-0 group-hover:opacity-100 transition-all shadow-sm"
                          title="Delete complaint"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                      {deleteConfirmId === postId && (
                        <div className="mt-2 mx-1 p-3 bg-red-50 border border-red-200 rounded-xl flex items-center justify-between gap-3">
                          <p className="text-xs text-red-700 font-medium flex-1">Delete this complaint? Authorities can still see the record.</p>
                          <div className="flex gap-2 shrink-0">
                            <button
                              onClick={() => setDeleteConfirmId(null)}
                              className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 font-semibold"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={() => handleDeleteComplaint(postId)}
                              disabled={isDeleting}
                              className="text-xs px-3 py-1.5 rounded-lg bg-srec-danger text-white font-semibold hover:bg-srec-dangerDark disabled:opacity-50"
                            >
                              {isDeleting ? 'Deleting…' : 'Delete'}
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          );
        })()}
      </div>

      {user?.role === 'Student' && <BottomNav />}
    </div>
  );
}
