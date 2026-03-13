import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ChevronDown, ChevronUp, HelpCircle, FileText, Cpu, EyeOff, ThumbsUp, BarChart2, ShieldCheck, ArrowLeft } from 'lucide-react';

/* ── Status badge helper ── */
function StatusBadge({ label, color }) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${color}`}>
      {label}
    </span>
  );
}

/* ── Accordion item ── */
function AccordionSection({ id, icon: Icon, title, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  const location = useLocation();

  /* Auto-open when hash matches this section */
  useEffect(() => {
    if (location.hash === `#${id}`) {
      setOpen(true);
      // Scroll to section after a tick so it has time to expand
      setTimeout(() => {
        document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 80);
    }
  }, [location.hash, id]);

  return (
    <div id={id} className="bg-white border border-[#E5E7EB] rounded-xl overflow-hidden shadow-sm">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-[#F8FAF8] transition-colors duration-150"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[#14532D]/10 flex items-center justify-center flex-shrink-0">
            <Icon size={16} className="text-[#14532D]" />
          </div>
          <span className="font-semibold text-[#111827]">{title}</span>
        </div>
        {open
          ? <ChevronUp size={18} className="text-[#6B7280] flex-shrink-0" />
          : <ChevronDown size={18} className="text-[#6B7280] flex-shrink-0" />}
      </button>

      {open && (
        <div className="px-5 pb-5 pt-1 text-sm text-[#374151] leading-relaxed border-t border-[#E5E7EB] space-y-3">
          {children}
        </div>
      )}
    </div>
  );
}

/* ── Step list ── */
function Steps({ items }) {
  return (
    <ol className="space-y-2 mt-2">
      {items.map((item, i) => (
        <li key={i} className="flex gap-3">
          <span className="flex-shrink-0 w-6 h-6 rounded-full bg-[#14532D] text-white text-xs font-bold flex items-center justify-center mt-0.5">
            {i + 1}
          </span>
          <span>{item}</span>
        </li>
      ))}
    </ol>
  );
}

/* ── Main page ── */
export default function HelpCenter() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#F8FAF8]">
      {/* Page header */}
      <div className="bg-[#14532D] text-white">
        <div className="max-w-[900px] mx-auto px-4 md:px-8 py-6 flex items-center gap-4">
          <button
            onClick={() => navigate(-1)}
            className="p-2 rounded-full hover:bg-white/20 transition-colors"
            aria-label="Go back"
          >
            <ArrowLeft size={20} />
          </button>
          <div className="flex items-center gap-3">
            <HelpCircle size={28} />
            <div>
              <h1 className="text-xl font-bold tracking-tight">Help Center</h1>
              <p className="text-sm text-white/75 mt-0.5">Everything you need to know about CampusVoice</p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-[900px] mx-auto px-4 md:px-8 py-6 md:py-8 space-y-4">

        {/* A — Getting Started */}
        <AccordionSection id="complaint-submission" icon={FileText} title="Getting Started" defaultOpen>
          <p>
            CampusVoice allows students to raise campus-related issues which are automatically routed
            to the correct authority using AI.
          </p>
          <Steps items={[
            'Tap "Posts" in the navigation bar.',
            'Describe the problem clearly in the text field.',
            'Attach an image as evidence if available.',
            'Choose complaint visibility — Public or Private.',
            'Submit your complaint.',
          ]} />
          <p className="text-[#6B7280] text-xs mt-2">
            💡 Be specific about the location (e.g. "ECE Lab Block B") so AI routes it faster.
          </p>
        </AccordionSection>

        {/* B — AI Complaint Routing */}
        <AccordionSection id="ai-routing" icon={Cpu} title="How AI Categorizes Complaints">
          <p>
            When you submit a complaint, our AI model reads the text and automatically identifies:
          </p>
          <ul className="space-y-1.5 mt-2">
            {[
              'Complaint category (Infrastructure, Academics, Hostel, etc.)',
              'Relevant department or authority',
              'Priority level (Low → Critical)',
              'Responsible person to notify',
            ].map((item, i) => (
              <li key={i} className="flex gap-2 items-start">
                <span className="text-[#22C55E] mt-0.5 flex-shrink-0">✓</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
          <div className="mt-3 p-3 bg-[#F8FAF8] border border-[#E5E7EB] rounded-lg text-xs">
            <span className="font-semibold text-[#14532D]">Example:</span>{' '}
            <span className="italic">"ECE Lab equipment broken"</span>
            {' → '}
            <span className="font-medium">Routed to ECE HOD</span>
          </div>
        </AccordionSection>

        {/* C — Anonymous Posting */}
        <AccordionSection id="anonymous" icon={EyeOff} title="Anonymous Posting">
          <p>
            Public complaints are <strong>anonymous to other students</strong>. Your name and roll
            number are never shown on the complaint feed.
          </p>
          <p>
            Your identity is only visible to <strong>administrators</strong> for verification
            purposes — and only when strictly necessary.
          </p>
          <p>
            Private complaints are only visible to the assigned authority and administrators.
          </p>
        </AccordionSection>

        {/* D — Voting System */}
        <AccordionSection id="voting" icon={ThumbsUp} title="How Voting Works">
          <p>
            Students can <strong>upvote</strong> complaints they also face on campus.
          </p>
          <ul className="space-y-1.5 mt-2">
            {[
              'Each student can vote once per complaint.',
              'More upvotes = higher complaint priority.',
              'Authorities see vote counts to identify the most urgent issues.',
              'You cannot vote on your own complaint.',
            ].map((item, i) => (
              <li key={i} className="flex gap-2 items-start">
                <span className="text-[#22C55E] mt-0.5 flex-shrink-0">✓</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
          <p className="text-[#6B7280] text-xs mt-2">
            💡 If you find a similar existing complaint, consider upvoting it instead of submitting a new one.
          </p>
        </AccordionSection>

        {/* E — Complaint Status */}
        <AccordionSection id="status" icon={BarChart2} title="Complaint Status Tracking">
          <p>Every complaint moves through defined stages:</p>
          <div className="mt-3 space-y-2">
            <div className="flex items-center gap-3">
              <StatusBadge label="Raised" color="bg-blue-100 text-blue-700" />
              <span className="text-[#6B7280] text-xs">Your complaint has been submitted and is awaiting review.</span>
            </div>
            <div className="flex items-center gap-3">
              <StatusBadge label="In Progress" color="bg-teal-100 text-teal-700" />
              <span className="text-[#6B7280] text-xs">An authority is actively working on your issue.</span>
            </div>
            <div className="flex items-center gap-3">
              <StatusBadge label="Resolved" color="bg-green-100 text-green-700" />
              <span className="text-[#6B7280] text-xs">The issue has been addressed and marked as resolved.</span>
            </div>
            <div className="flex items-center gap-3">
              <StatusBadge label="Closed" color="bg-gray-100 text-gray-600" />
              <span className="text-[#6B7280] text-xs">The complaint is closed — no further action required.</span>
            </div>
            <div className="flex items-center gap-3">
              <StatusBadge label="Spam" color="bg-red-100 text-red-600" />
              <span className="text-[#6B7280] text-xs">Flagged as spam or invalid by the AI moderation system.</span>
            </div>
          </div>
          <p className="text-[#6B7280] text-xs mt-3">
            You can track your complaints under <strong>Posts → My Posts</strong>.
          </p>
        </AccordionSection>

        {/* F — Privacy & Safety */}
        <AccordionSection id="privacy" icon={ShieldCheck} title="Privacy & Safety">
          <p>
            CampusVoice is designed with student privacy as a priority.
          </p>
          <ul className="space-y-1.5 mt-2">
            {[
              'Only authorized authorities can view your identity when strictly necessary.',
              'Your personal data is never shared with other students.',
              'Spam complaints may be flagged automatically by the AI moderation system.',
              'Misuse of the platform (spam, false complaints) may result in account review.',
            ].map((item, i) => (
              <li key={i} className="flex gap-2 items-start">
                <span className="text-[#22C55E] mt-0.5 flex-shrink-0">✓</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </AccordionSection>

        {/* Footer note */}
        <p className="text-center text-xs text-[#6B7280] py-4">
          Need more help? Contact your Student Representative or the Academic Office.
        </p>
      </div>
    </div>
  );
}
