import React from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft, Home, FileText, Bell, Award, Users, MessageSquare,
  ThumbsUp, ShieldCheck, HelpCircle,
} from 'lucide-react';

/* ── Status badge ── */
function StatusBadge({ label, color }) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${color}`}>
      {label}
    </span>
  );
}

/* ── Numbered step list ── */
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

/* ── Bullet list ── */
function Bullets({ items }) {
  return (
    <ul className="space-y-1.5 mt-2">
      {items.map((item, i) => (
        <li key={i} className="flex gap-2 items-start">
          <span className="text-[#22C55E] mt-0.5 flex-shrink-0">✓</span>
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

/* ── Tip box ── */
function Tip({ children }) {
  return (
    <div className="mt-3 p-3 bg-emerald-50 border border-emerald-100 rounded-lg text-xs text-emerald-800">
      💡 {children}
    </div>
  );
}

/* ── Section card (always expanded — used in context mode) ── */
function SectionCard({ icon: Icon, title, children }) {
  return (
    <div className="bg-white border border-[#E5E7EB] rounded-xl overflow-hidden shadow-sm">
      <div className="flex items-center gap-3 px-5 py-4 border-b border-[#E5E7EB] bg-[#F8FAF8]">
        <div className="w-8 h-8 rounded-lg bg-[#14532D]/10 flex items-center justify-center flex-shrink-0">
          <Icon size={16} className="text-[#14532D]" />
        </div>
        <span className="font-semibold text-[#111827]">{title}</span>
      </div>
      <div className="px-5 py-4 text-sm text-[#374151] leading-relaxed space-y-3">
        {children}
      </div>
    </div>
  );
}

/* ── All help sections ── */
const SECTIONS = {
  'campus-feed': (
    <SectionCard key="campus-feed" icon={Home} title="Using the Campus Feed">
      <p>The <strong>Campus Feed</strong> shows all complaints raised by students on campus. Scroll to see what issues others are facing and support them by voting.</p>
      <Steps items={[
        'Scroll down to browse complaints. Each card shows the category, status, and vote count.',
        'Tap any complaint to see full details and status updates from the authority handling it.',
        'Use Hot / New / Top buttons to change the sort order.',
        'Tap Filters to search by keyword, status, priority, or category.',
        'Paste a complaint\'s short code (like E28E3A) in the search box to jump directly to it.',
      ]} />
      <Tip>Pull down on the feed to refresh and see the latest complaints.</Tip>
    </SectionCard>
  ),
  'raise-complaint': (
    <SectionCard key="raise-complaint" icon={FileText} title="How to raise a complaint">
      <p>Use the <strong>Posts</strong> tab to report a campus problem. The app automatically sends it to the right authority.</p>
      <Steps items={[
        'Tap the red "Raise an Issue" button.',
        'Describe the problem clearly — mention the exact location (e.g. "ECE Lab, Block B, Room 203").',
        'Optionally attach a photo. Taking a photo with your camera adds your GPS location automatically.',
        'Choose visibility: Public (all students can see) or Private (only you and the authority).',
        'Tap Submit. The AI categorises your complaint and routes it instantly.',
      ]} />
      <p className="mt-2"><strong>What happens next?</strong> Your complaint appears under "My Posts" with status <em>Raised</em>. You will be notified when the authority takes action.</p>
      <Tip>If a similar complaint already exists, you will be shown a match. Upvote that instead — combined votes carry more weight.</Tip>
    </SectionCard>
  ),
  'my-posts': (
    <SectionCard key="my-posts" icon={FileText} title="Tracking your complaints">
      <p>Go to <strong>Posts → My Posts</strong> to see all your complaints and their current status.</p>
      <div className="mt-3 space-y-2.5">
        <div className="flex items-start gap-3">
          <StatusBadge label="Raised" color="bg-blue-100 text-blue-700" />
          <span className="text-[#6B7280] text-xs pt-0.5">Received — waiting for an authority to pick it up.</span>
        </div>
        <div className="flex items-start gap-3">
          <StatusBadge label="In Progress" color="bg-teal-100 text-teal-700" />
          <span className="text-[#6B7280] text-xs pt-0.5">An authority is actively working on fixing the issue.</span>
        </div>
        <div className="flex items-start gap-3">
          <StatusBadge label="Resolved" color="bg-green-100 text-green-700" />
          <span className="text-[#6B7280] text-xs pt-0.5">Fixed. You can rate how satisfied you are with the resolution.</span>
        </div>
        <div className="flex items-start gap-3">
          <StatusBadge label="Closed" color="bg-gray-100 text-gray-600" />
          <span className="text-[#6B7280] text-xs pt-0.5">Closed with no further action needed.</span>
        </div>
        <div className="flex items-start gap-3">
          <StatusBadge label="Spam" color="bg-red-100 text-red-600" />
          <span className="text-[#6B7280] text-xs pt-0.5">Marked invalid. Repeated spam may affect your account.</span>
        </div>
      </div>
      <Tip>Tap any complaint to see the full timeline — who handled it, what actions were taken, and authority notes.</Tip>
    </SectionCard>
  ),
  'voting': (
    <SectionCard key="voting" icon={ThumbsUp} title="How voting works">
      <p>Voting tells authorities <strong>how many students are affected</strong>. Complaints with more upvotes get higher priority automatically.</p>
      <Bullets items={[
        'Tap thumbs-up on any complaint card to upvote it.',
        'Tap thumbs-down if you think it is not a genuine issue.',
        'You can vote once per complaint. Tap the same button again to remove your vote.',
        'You cannot vote on your own complaints.',
        'High vote counts push a complaint to Critical priority — resolved fastest.',
      ]} />
      <Tip>If you face the same problem as an existing complaint, upvote it rather than submitting a new one.</Tip>
    </SectionCard>
  ),
  'petitions': (
    <SectionCard key="petitions" icon={Users} title="Petitions — collective campus action">
      <p><strong>Petitions</strong> are formal requests for a campus change — like adding a facility or updating a rule. They need signatures to be considered.</p>
      <Steps items={[
        'Tap "Petitions" in the Community section.',
        'Read ongoing petitions and tap "Sign this Petition" if you support it.',
        'If you are a Student Representative, tap "Start Petition" to create one.',
        'Set a clear title, description, and the number of signatures needed.',
        'Once your petition expires or reaches its goal, relevant authorities are notified.',
      ]} />
      <Bullets items={[
        'Signing is blocked after the petition deadline expires.',
        'Only appointed Student Representatives can create petitions.',
        'You can create one petition every 7 days.',
        'Reaching 50, 100, or 250 signatures triggers automatic authority notification.',
      ]} />
    </SectionCard>
  ),
  'notices': (
    <SectionCard key="notices" icon={Bell} title="Reading notices">
      <p>Authorities publish <strong>Notices</strong> for official announcements — maintenance schedules, policy updates, exam timetables, and more.</p>
      <Steps items={[
        'Tap "Notices" in the bottom navigation bar.',
        'Scroll to browse — notices are sorted newest first.',
        'Tap any notice to read its full content.',
        'If there is an attachment (PDF or image), tap the attachment icon to open or download it.',
      ]} />
    </SectionCard>
  ),
  'wins': (
    <SectionCard key="wins" icon={Award} title="What's Fixed — resolved complaints">
      <p>The <strong>What&apos;s Fixed</strong> page shows popular complaints that were resolved — real improvements made because students raised their voices.</p>
      <Bullets items={[
        'Only complaints with significant upvotes that got resolved appear here.',
        'See how quickly each issue was resolved and any note from the authority.',
        'Your satisfaction rating (after a resolution) contributes to the score shown.',
        'This page refreshes daily with a rolling 7-day window.',
      ]} />
    </SectionCard>
  ),
  'anonymous': (
    <SectionCard key="anonymous" icon={ShieldCheck} title="Privacy — your identity is protected">
      <p>CampusVoice is designed so you can speak up without fear.</p>
      <Bullets items={[
        'Public complaints show as "Anonymous" to other students — your name and roll number are never visible on the feed.',
        'Only the assigned authority and the Admin can see who submitted a complaint, and only when needed to resolve it.',
        'Private complaints are only visible to you, the authority, and the Admin.',
        'Your votes are also private — no one can see how you voted.',
        'Misusing the platform (spam, false reports) may lead to your account being reviewed.',
      ]} />
      <Tip>For sensitive issues like harassment or safety concerns, set the complaint to <strong>Private</strong> — it still reaches the right authority but is not visible to other students.</Tip>
    </SectionCard>
  ),
  'shortcode': (
    <SectionCard key="shortcode" icon={MessageSquare} title="Complaint short codes">
      <p>Every complaint has a unique <strong>short code</strong> (like <code className="bg-gray-100 px-1 rounded">E28E3A</code>) shown at the bottom of the card.</p>
      <Bullets items={[
        'Tap the short code to copy it.',
        'Open Filters in the Campus Feed and paste the code in the search box to find that exact complaint.',
        'Share the short code with a friend so they can find and upvote the same complaint.',
      ]} />
    </SectionCard>
  ),
  'complaint-detail': (
    <SectionCard key="complaint-detail" icon={FileText} title="Reading a complaint in detail">
      <p>Tapping a complaint opens its <strong>full detail view</strong> with the complete description, status history, and authority updates.</p>
      <Bullets items={[
        'See every status change and when it happened.',
        'Read public updates posted by the authority handling the complaint.',
        'If the complaint is resolved, you can leave a satisfaction rating.',
        'Tap the back button to return to the feed where you left off — your scroll position is saved.',
      ]} />
    </SectionCard>
  ),
};

// Which sections to show per page key
const PAGE_SECTIONS = {
  'campus-feed':      ['campus-feed', 'voting', 'shortcode', 'anonymous'],
  'posts':            ['raise-complaint', 'my-posts', 'anonymous'],
  'petitions':        ['petitions'],
  'wins':             ['wins'],
  'notices':          ['notices'],
  'complaint-detail': ['complaint-detail', 'voting', 'anonymous'],
  'privacy':          ['anonymous'],
};

const PAGE_LABELS = {
  'campus-feed': 'Campus Feed',
  'posts': 'Posts',
  'petitions': 'Petitions',
  'wins': "What's Fixed",
  'notices': 'Notices',
  'complaint-detail': 'Complaint Detail',
  'privacy': 'Profile',
};

/* ── Main page ── */
export default function HelpCenter() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const location = useLocation();

  const from = searchParams.get('from'); // e.g. "campus-feed", "posts", or null
  const isContextMode = from && from !== 'all' && PAGE_SECTIONS[from];

  const sectionsToShow = isContextMode
    ? PAGE_SECTIONS[from]
    : Object.keys(SECTIONS);

  const pageLabel = isContextMode ? PAGE_LABELS[from] : null;

  // Auto-scroll to hash if present
  React.useEffect(() => {
    if (location.hash) {
      const id = location.hash.slice(1);
      setTimeout(() => {
        document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    }
  }, [location.hash]);

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
              <h1 className="text-xl font-bold tracking-tight">
                {pageLabel ? `Help — ${pageLabel}` : 'Help Center'}
              </h1>
              <p className="text-sm text-white/75 mt-0.5">
                {pageLabel
                  ? `How to use the ${pageLabel} page`
                  : 'Simple guides for every page in CampusVoice'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-[900px] mx-auto px-4 md:px-8 py-6 md:py-8 space-y-4">

        {/* Show all-topics link when in context mode */}
        {isContextMode && (
          <button
            onClick={() => navigate('/help')}
            className="text-xs text-[#14532D] font-medium hover:underline flex items-center gap-1"
          >
            ← See all help topics
          </button>
        )}

        {sectionsToShow.map(key => {
          const section = SECTIONS[key];
          if (!section) return null;
          return <div key={key} id={key}>{section}</div>;
        })}

        <p className="text-center text-xs text-[#6B7280] py-4">
          Still stuck? Speak to your Student Representative or visit the Academic Office.
        </p>
      </div>
    </div>
  );
}
