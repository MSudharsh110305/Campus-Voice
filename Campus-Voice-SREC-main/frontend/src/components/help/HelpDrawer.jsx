import React from 'react';
import { X, ChevronRight, FileText, Cpu, EyeOff, ThumbsUp, BarChart2, ShieldCheck } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const TOPICS = [
  { icon: FileText,   title: 'How to raise a complaint',        hash: 'complaint-submission' },
  { icon: Cpu,        title: 'How AI categorizes complaints',   hash: 'ai-routing' },
  { icon: EyeOff,     title: 'Anonymous posting',               hash: 'anonymous' },
  { icon: ThumbsUp,   title: 'How voting works',                hash: 'voting' },
  { icon: BarChart2,  title: 'Complaint status tracking',       hash: 'status' },
  { icon: ShieldCheck,title: 'Who receives complaints',         hash: 'privacy' },
];

export default function HelpDrawer({ isOpen, onClose }) {
  const navigate = useNavigate();

  const goToSection = (hash) => {
    navigate(`/help#${hash}`);
    onClose();
  };

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
          <span className="text-lg font-semibold text-[#14532D]">CampusVoice Help</span>
          <button
            onClick={onClose}
            className="p-2 rounded-full hover:bg-gray-100 transition-colors text-gray-500"
            aria-label="Close help drawer"
          >
            <X size={18} />
          </button>
        </div>

        {/* Topics list */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-400 mb-1">
            Quick Help Topics
          </p>

          {TOPICS.map((topic) => {
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
          })}
        </div>

        {/* Footer — full help center */}
        <div className="px-4 py-4 border-t border-[#E5E7EB]">
          <button
            onClick={() => { navigate('/help'); onClose(); }}
            className="w-full py-3 rounded-xl bg-[#14532D] hover:bg-[#166534] text-white font-semibold text-sm transition-colors duration-200"
          >
            View Full Help Center
          </button>
        </div>
      </div>
    </>
  );
}
