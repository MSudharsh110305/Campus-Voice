import React from 'react';
import { X, ChevronRight, Home, FileText, Bell, Award, Users, MessageSquare, ThumbsUp, ShieldCheck } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

// All topics mapped to their page key(s)
const ALL_TOPICS = [
  { icon: Home,          title: 'Using the Campus Feed',          hash: 'campus-feed',       pages: ['campus-feed', 'complaint-detail'] },
  { icon: FileText,      title: 'How to raise a complaint',       hash: 'raise-complaint',   pages: ['posts'] },
  { icon: FileText,      title: 'Tracking your complaints',       hash: 'my-posts',          pages: ['posts', 'complaint-detail'] },
  { icon: ThumbsUp,      title: 'How voting works',               hash: 'voting',            pages: ['campus-feed', 'complaint-detail'] },
  { icon: Users,         title: 'Petitions — how they work',      hash: 'petitions',         pages: ['petitions'] },
  { icon: Bell,          title: 'Reading notices',                hash: 'notices',           pages: ['notices'] },
  { icon: Award,         title: "What's Fixed — resolved wins",   hash: 'wins',              pages: ['wins'] },
  { icon: ShieldCheck,   title: 'Privacy & your identity',        hash: 'anonymous',         pages: ['posts', 'privacy', 'complaint-detail', 'campus-feed'] },
  { icon: MessageSquare, title: 'Using complaint short codes',    hash: 'shortcode',         pages: ['campus-feed'] },
];

export default function HelpDrawer({ isOpen, onClose, pageKey }) {
  const navigate = useNavigate();

  // Filter topics to current page; if pageKey is null show all
  const topics = pageKey
    ? ALL_TOPICS.filter(t => t.pages.includes(pageKey))
    : ALL_TOPICS;

  const goToSection = (hash) => {
    navigate(`/help?from=${pageKey || 'all'}#${hash}`);
    onClose();
  };

  const pageLabel = {
    'campus-feed': 'Campus Feed',
    'posts': 'Posts',
    'petitions': 'Petitions',
    'wins': "What's Fixed",
    'notices': 'Notices',
    'complaint-detail': 'Complaint Detail',
    'privacy': 'Profile',
  }[pageKey] || 'CampusVoice';

  return (
    <>
      {/* Mobile backdrop */}
      <div
        onClick={onClose}
        className={`fixed inset-0 bg-black/30 z-40 md:hidden transition-opacity duration-300 ${
          isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
      />

      {/* Drawer panel */}
      <div
        className={`fixed top-0 right-0 h-full z-50 bg-white shadow-2xl flex flex-col
          transition-transform duration-300 ease-in-out
          w-full md:w-[360px]
          ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#E5E7EB]">
          <div>
            <span className="text-base font-semibold text-[#14532D]">Help — {pageLabel}</span>
            <p className="text-[11px] text-gray-400 mt-0.5">Tips for this page</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-full hover:bg-gray-100 transition-colors text-gray-500"
            aria-label="Close help drawer"
          >
            <X size={18} />
          </button>
        </div>

        {/* Topics list */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-2">
          {topics.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">No tips for this page yet.</p>
          ) : (
            topics.map((topic) => {
              const Icon = topic.icon;
              return (
                <div
                  key={topic.hash}
                  onClick={() => goToSection(topic.hash)}
                  className="bg-white border border-[#E5E7EB] rounded-xl p-4 cursor-pointer hover:shadow-md transition-all duration-200 flex items-center gap-3"
                >
                  <div className="w-9 h-9 rounded-lg bg-[#14532D]/10 flex items-center justify-center flex-shrink-0">
                    <Icon size={16} className="text-[#14532D]" />
                  </div>
                  <span className="flex-1 text-sm font-medium text-[#111827]">{topic.title}</span>
                  <ChevronRight size={15} className="text-gray-400 flex-shrink-0" />
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-4 border-t border-[#E5E7EB] space-y-2">
          <button
            onClick={() => { navigate(`/help?from=${pageKey || 'all'}`); onClose(); }}
            className="w-full py-3 rounded-xl bg-[#14532D] hover:bg-[#166534] text-white font-semibold text-sm transition-colors duration-200"
          >
            View Full Help for This Page
          </button>
          {pageKey && (
            <button
              onClick={() => { navigate('/help'); onClose(); }}
              className="w-full py-2 rounded-xl text-gray-400 text-xs hover:text-gray-600 transition-colors"
            >
              See all help topics
            </button>
          )}
        </div>
      </div>
    </>
  );
}
