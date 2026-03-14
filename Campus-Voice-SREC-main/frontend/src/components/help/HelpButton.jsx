import React, { useEffect, useRef, useState } from 'react';
import { HelpCircle } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';

// Map current pathname to a page key used by HelpCenter
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
  const location = useLocation();
  const navigate = useNavigate();
  const pageKey = getPageKey(location.pathname);
  const [visible, setVisible] = useState(true);

  // Don't show help button when already on the help page
  if (location.pathname.startsWith('/help')) return null;
  const lastScrollY = useRef(0);
  const ticking = useRef(false);

  useEffect(() => {
    const handleScroll = () => {
      if (!ticking.current) {
        window.requestAnimationFrame(() => {
          const currentY = window.scrollY;
          if (currentY < 60) {
            setVisible(true);
          } else {
            setVisible(currentY < lastScrollY.current);
          }
          lastScrollY.current = currentY;
          ticking.current = false;
        });
        ticking.current = true;
      }
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const handleClick = () => {
    navigate(pageKey ? `/help?from=${pageKey}` : '/help');
  };

  return (
    <button
      onClick={handleClick}
      className={`fixed bottom-20 right-4 md:bottom-5 md:right-5 z-40
        w-11 h-11 md:w-12 md:h-12
        rounded-full shadow-lg
        bg-[#14532D] hover:bg-[#166534]
        text-white flex items-center justify-center
        transition-all duration-300
        hover:scale-110 active:scale-95
        ${visible ? 'opacity-100 translate-y-0 pointer-events-auto' : 'opacity-0 translate-y-4 pointer-events-none'}`}
      aria-label="Open help"
    >
      <HelpCircle size={20} />
    </button>
  );
}
