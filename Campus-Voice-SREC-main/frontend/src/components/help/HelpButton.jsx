import React, { useState } from 'react';
import { HelpCircle } from 'lucide-react';
import HelpDrawer from './HelpDrawer';

export default function HelpButton() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {/*
        Mobile: bottom-20 (80px) — clears the 64px BottomNav + margin
        Desktop: md:bottom-5 (20px), md:right-5 (20px)
      */}
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

      <HelpDrawer isOpen={isOpen} onClose={() => setIsOpen(false)} />
    </>
  );
}
