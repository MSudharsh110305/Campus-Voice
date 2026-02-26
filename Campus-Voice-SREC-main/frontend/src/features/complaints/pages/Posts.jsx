import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { TopNav } from '../../../components/Navbars';
import BottomNav from '../../../components/BottomNav';
import { Card, Button, EliteButton } from '../../../components/UI';
import ComplaintCard from '../components/ComplaintCard';
import { useAuth } from '../../../context/AuthContext';
import complaintService from '../../../services/complaint.service';
import studentService from '../../../services/student.service';
import { Upload, X, Lock, FileX, Inbox } from 'lucide-react';
import { VISIBILITY, COMPLAINT_CATEGORIES } from '../../../utils/constants';

export default function Posts() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('create');
  const [formData, setFormData] = useState({
    original_text: '',
    image: null,
    visibility: 'Public',
  });
  const [imagePreview, setImagePreview] = useState(null);
  const [myPosts, setMyPosts] = useState([]);
  const [submitted, setSubmitted] = useState(false);
  const [apiResponse, setApiResponse] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState('');

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? checked : value,
    });
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
  }, [activeTab]);

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

    setIsSubmitting(true);

    try {
      const fd = new FormData();
      fd.append('original_text', formData.original_text);
      fd.append('visibility', formData.visibility);
      if (formData.image) {
        fd.append('image', formData.image);
      }

      const response = await complaintService.submitComplaint(fd);

      setApiResponse(response);
      setSubmitted(true);

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

      setFormData({
        original_text: '',
        image: null,
        visibility: 'Public',
      });
      setImagePreview(null);

    } catch (error) {
      console.error(error);
      setFormError(error.message || 'Failed to submit complaint');
    } finally {
      setIsSubmitting(false);
    }
  };

  const inputClass = "w-full rounded-xl border border-gray-200 bg-gray-50/50 px-4 py-3 text-sm text-gray-900 placeholder:text-gray-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary transition-all";

  // Success screen
  if (submitted && apiResponse) {
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

            <div className="pt-4 border-t border-gray-200">
              <span className="text-xs text-gray-400 uppercase tracking-wide font-bold">AI Rephrased Complaint</span>
              <p className="text-sm text-gray-700 mt-1 italic leading-relaxed">"{apiResponse.rephrased_text || apiResponse.summary || 'Processing...'}"</p>
            </div>

            {apiResponse.has_image && apiResponse.image_verification_status && (
              <div className="pt-4 border-t border-gray-200">
                <span className="text-xs text-gray-400 uppercase tracking-wide font-bold">Image Verification</span>
                <p className={`text-sm mt-1 ${apiResponse.image_verified ? 'text-green-600' : 'text-orange-600'}`}>
                  {apiResponse.image_verification_message || apiResponse.image_verification_status}
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
                setActiveTab('mine');
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
          <h1 className="text-xl font-bold text-gray-900 tracking-tight">Posts</h1>

          {/* Pill tab switcher */}
          <div className="flex bg-gray-100 rounded-full p-1">
            <button
              onClick={() => setActiveTab('create')}
              className={`px-4 py-1.5 text-sm font-medium rounded-full transition-all duration-200 ${activeTab === 'create'
                ? 'bg-white shadow-sm text-srec-primary font-semibold'
                : 'text-gray-500 hover:text-gray-700'
                }`}
            >
              Create
            </button>
            <button
              onClick={() => setActiveTab('mine')}
              className={`px-4 py-1.5 text-sm font-medium rounded-full transition-all duration-200 ${activeTab === 'mine'
                ? 'bg-white shadow-sm text-srec-primary font-semibold'
                : 'text-gray-500 hover:text-gray-700'
                }`}
            >
              My Posts
            </button>
          </div>
        </div>

        {activeTab === 'create' && (
          <Card className="p-5 sm:p-6 shadow-sm">
            {/* Privacy Reassurance Banner */}
            <div className="flex items-center gap-3 p-4 mb-5 rounded-xl bg-amber-50 border border-amber-100">
              <div className="flex-shrink-0 w-9 h-9 rounded-full bg-amber-100 flex items-center justify-center text-amber-600">
                <Lock size={16} />
              </div>
              <div>
                <h4 className="text-sm font-bold text-amber-800">Anonymous Posting</h4>
                <p className="text-xs text-amber-700/80 mt-0.5">
                  Your identity is hidden from other students. Only authorities can see your details.
                </p>
              </div>
            </div>

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
                  <label className={`flex-1 flex items-center justify-center gap-2 p-3 rounded-xl border cursor-pointer transition-all duration-200 ${formData.visibility === 'Public' ? 'border-srec-primary bg-srec-primary/5 text-srec-primary shadow-sm' : 'border-gray-200 bg-white hover:bg-gray-50 text-gray-600'}`}>
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
                  <label className={`flex-1 flex items-center justify-center gap-2 p-3 rounded-xl border cursor-pointer transition-all duration-200 ${formData.visibility === 'Private' ? 'border-amber-500 bg-amber-50 text-amber-700 shadow-sm' : 'border-gray-200 bg-white hover:bg-gray-50 text-gray-600'}`}>
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
                {!imagePreview ? (
                  <label className="flex flex-col items-center justify-center w-full h-28 border-2 border-dashed border-gray-200 rounded-xl cursor-pointer bg-gray-50 hover:bg-gray-100 transition-colors">
                    <Upload className="w-7 h-7 mb-1.5 text-gray-400" />
                    <p className="text-xs text-gray-500 font-medium">Click to upload photo (optional, max 5MB)</p>
                    <input type="file" className="hidden" accept="image/*" onChange={handleImageChange} />
                  </label>
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
                disabled={isSubmitting}
                className="w-full py-3 bg-srec-primary text-white font-semibold rounded-xl hover:bg-srec-primaryHover transition-all duration-200 shadow-sm disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {isSubmitting ? 'Submitting...' : 'Submit Grievance'}
              </button>
            </form>
          </Card>
        )}

        {/* My Posts tab */}
        {activeTab === 'mine' && (
          <div className="space-y-3">
            {(!Array.isArray(myPosts) || myPosts.length === 0) ? (
              <div className="text-center py-16 bg-white rounded-2xl border border-gray-100 shadow-sm">
                <div className="w-14 h-14 mx-auto mb-3 rounded-full bg-gray-50 flex items-center justify-center">
                  <Inbox size={26} className="text-gray-400" />
                </div>
                <p className="text-gray-700 text-base font-semibold">No posts yet</p>
                <p className="text-gray-400 text-sm mt-1 max-w-xs mx-auto">
                  Your submitted complaints will appear here
                </p>
                <button
                  className="mt-4 text-sm text-srec-primary font-semibold hover:underline"
                  onClick={() => setActiveTab('create')}
                >
                  Raise your first issue
                </button>
              </div>
            ) : (
              myPosts.map((post) => (
                <ComplaintCard
                  key={post.id || post.complaint_id}
                  id={post.id || post.complaint_id}
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
                />
              ))
            )}
          </div>
        )}
      </div>

      {user?.role === 'Student' && <BottomNav />}
    </div>
  );
}
