import React, { useState } from 'react';
import { HelpCircle } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import HelpDrawer from './HelpDrawer';

// Map current pathname to a page key used by HelpDrawer and HelpCenter
export function getPageKey(pathname) {
  if (pathname === '/' || pathname === '/home') return 'campus-feed';
  if (pathname.startsWith('/posts')) return 'posts';
  if (pathname.startsWith('/petitions')) return 'petitions';
  if (pathname.startsWith('/wins')) return 'wins';
  if (pathname.startsWith('/notices')) return 'notices';
  if (pathname.startsWith('/complaint/')) return 'complaint-detail';
  if (pathname.startsWith('/profile')) return 'privacy';
  return null;
}

export default function HelpButton() {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();
  const pageKey = getPageKey(location.pathname);

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-20 right-4 md:bottom-5 md:right-5 z-40
          w-12 h-12 md:w-[52px] md:h-[52px]
          rounded-full shadow-lg
          bg-[#14532D] hover:bg-[#166534]
          text-white flex items-center justify-center
          transition-all duration-200 hover:scale-110 active:scale-95"
        aria-label="Open help"
      >
        <HelpCircle size={22} />
      </button>

      <HelpDrawer isOpen={isOpen} onClose={() => setIsOpen(false)} pageKey={pageKey} />
    </>
  );
}
