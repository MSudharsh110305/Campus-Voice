import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { TopNav } from '../../../components/Navbars';
import BottomNav from '../../../components/BottomNav';
import { Card } from '../../../components/UI';
import { useAuth } from '../../../context/AuthContext';
import complaintService from '../../../services/complaint.service';


export default function SubmitComplaint() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ title: '', description: '', image: null, visibility: 'Public' });
  const [imagePreview, setImagePreview] = useState(null);
  const [submitted, setSubmitted] = useState(false);
  const [showCheckmark, setShowCheckmark] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [spamWarning, setSpamWarning] = useState(null);
  const [submitResult, setSubmitResult] = useState(null);

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setForm({ ...form, image: file });
      setImagePreview(URL.createObjectURL(file));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      // Create FormData for multipart upload
      const formData = new FormData();
      formData.append('original_text', form.description);
      formData.append('visibility', form.visibility);

      if (form.image) {
        formData.append('image', form.image);
      }

      // Submit to API
      const result = await complaintService.submitComplaint(formData);

      // If complaint was saved but marked as spam, show a soft warning
      if (result && result.is_spam) {
        setSpamWarning(result.message || 'Your complaint was received but flagged as potential spam. You may contact admin if this is genuine.');
      }

      // Store AI analysis results for display
      if (result) {
        setSubmitResult({
          category: result.category,
          priority: result.priority,
          assigned_authority: result.assigned_authority,
        });
      }

      // Show success animation
      setSubmitted(true);
      setShowCheckmark(true);

      // Redirect to home after showing success message (4 seconds)
      setTimeout(() => {
        navigate('/home');
      }, 4000);
    } catch (err) {
      console.error('Submission error:', err);
      const msg = err?.response?.data?.error
        || err?.response?.data?.detail
        || (typeof err?.response?.data === 'string' ? err.response.data : null)
        || (typeof err?.message === 'string' ? err.message : null)
        || 'Submission failed. Please try again.';
      setError(msg);
      setSubmitting(false);
    }
  };

  // Reset form when component unmounts or when navigating away
  useEffect(() => {
    return () => {
      if (!submitted) {
        setForm({ title: '', description: '', image: null });
        setImagePreview(null);
        const fileInput = document.querySelector('input[type="file"]');
        if (fileInput) fileInput.value = '';
      }
    };
  }, [submitted]);

  const isFormValid = form.description && form.image && !submitting;

  // Success screen (GPay-style)
  if (submitted) {
    return (
      <div className="fixed inset-0 z-50 min-h-screen bg-gradient-to-br from-green-50 to-blue-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full mx-auto p-8 text-center bg-white rounded-2xl shadow-xl">
          {/* Animated Success Circle with Checkmark */}
          <div className="mb-8 flex justify-center">
            <div className="relative w-32 h-32">
              {/* Outer Circle - animated drawing */}
              <svg className="w-32 h-32 transform -rotate-90" viewBox="0 0 120 120">
                <circle
                  cx="60"
                  cy="60"
                  r="54"
                  fill="none"
                  stroke="#10b981"
                  strokeWidth="6"
                  strokeLinecap="round"
                  strokeDasharray="339.292"
                  strokeDashoffset="339.292"
                  className="animate-drawCircle"
                />
              </svg>

              {/* Checkmark - appears after circle is drawn */}
              <div className="absolute inset-0 flex items-center justify-center opacity-0 animate-[fadeIn_0.3s_ease-out_0.6s_forwards]">
                <svg
                  className="w-16 h-16 text-green-600 animate-checkmark"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  style={{
                    strokeDasharray: 40,
                    strokeDashoffset: 40
                  }}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={4}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
            </div>
          </div>

          {/* Success Messages */}
          <div className="space-y-4 animate-fadeInDelay">
            <h2 className="text-2xl font-bold text-gray-900">
              {spamWarning ? 'Complaint Received' : 'Complaint Submitted Successfully!'}
            </h2>

            {spamWarning ? (
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-left">
                <p className="text-sm font-semibold text-amber-800 mb-1">⚠️ Flagged as Potential Spam</p>
                <p className="text-xs text-amber-700 leading-relaxed">{spamWarning}</p>
              </div>
            ) : (
              <>
                <p className="text-lg text-gray-700 leading-relaxed">
                  Your complaint has been submitted and routed.
                </p>
                {submitResult && (submitResult.category || submitResult.priority || submitResult.assigned_authority) ? (
                  <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 text-left mt-3 space-y-1">
                    {submitResult.category && (
                      <p className="text-sm text-blue-800">
                        <span className="font-semibold">Category:</span> {submitResult.category}
                      </p>
                    )}
                    {submitResult.priority && (
                      <p className="text-sm text-blue-800">
                        <span className="font-semibold">Priority:</span> {submitResult.priority}
                      </p>
                    )}
                    {submitResult.assigned_authority && (
                      <p className="text-sm text-blue-800">
                        <span className="font-semibold">Assigned to:</span> {submitResult.assigned_authority}
                      </p>
                    )}
                  </div>
                ) : null}
                <p className="text-base text-gray-600 leading-relaxed mt-2">
                  Thank you for your feedback. Your voice helps make SREC a better place.
                </p>
              </>
            )}
          </div>

          {/* Loading indicator */}
          <div className="mt-8 animate-fadeInDelay">
            <div className="inline-flex items-center gap-2 text-sm text-gray-500">
              <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0s' }}></div>
              <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
              <span className="ml-2">Redirecting...</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <TopNav />
      <div className="max-w-2xl mx-auto p-4 sm:p-6 pb-20 md:pl-20">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-semibold text-gray-900 mb-2">Submit a Complaint</h1>
          <p className="text-gray-600 text-sm">Please provide all required information</p>
        </div>

        <Card className="p-6 sm:p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Title <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="Brief title for your complaint"
                className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-gray-900 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent transition-all"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description <span className="text-red-500">*</span>
              </label>
              <textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="Describe your complaint in detail..."
                rows={5}
                className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-gray-900 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent transition-all resize-none"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Image <span className="text-red-500">*</span>
              </label>
              <div className="space-y-3">
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleImageChange}
                  className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent transition-all file:mr-4 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-brand file:text-white hover:file:bg-brand-dark file:cursor-pointer"
                  required
                />
                {imagePreview && (
                  <div className="mt-3">
                    <p className="text-xs text-gray-600 mb-2">Image Preview:</p>
                    <div className="relative rounded-lg overflow-hidden border border-gray-200">
                      <img
                        src={imagePreview}
                        alt="Preview"
                        className="w-full h-48 object-cover"
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Visibility
              </label>
              <div className="flex gap-4">
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="visibility"
                    value="Public"
                    checked={form.visibility === 'Public'}
                    onChange={(e) => setForm({ ...form, visibility: e.target.value })}
                    className="mr-2"
                  />
                  <span className="text-sm text-gray-700">Public</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="visibility"
                    value="Private"
                    checked={form.visibility === 'Private'}
                    onChange={(e) => setForm({ ...form, visibility: e.target.value })}
                    className="mr-2"
                  />
                  <span className="text-sm text-gray-700">Private</span>
                </label>
              </div>
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-600">
                {error}
              </div>
            )}

            <div className="pt-4">
              <button
                type="submit"
                disabled={!isFormValid}
                className="w-full bg-brand disabled:opacity-50 disabled:cursor-not-allowed hover:bg-brand-dark text-white rounded-lg px-6 py-3 font-medium transition-all duration-200 shadow-sm hover:shadow-md"
              >
                {submitting ? 'Submitting...' : 'Submit Complaint'}
              </button>
            </div>
          </form>
        </Card>
      </div>
      {user?.role === 'Student' && <BottomNav />}
    </div>
  );
}

