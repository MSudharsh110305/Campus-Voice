import React, { useState, useRef, useEffect } from 'react';
import { Info } from 'lucide-react';

export default function InfoTooltip({ text }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    const handleOutside = (e) => {
      if (ref.current && !ref.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutside);
    document.addEventListener('touchstart', handleOutside);
    return () => {
      document.removeEventListener('mousedown', handleOutside);
      document.removeEventListener('touchstart', handleOutside);
    };
  }, [open]);

  return (
    <div className="relative inline-flex items-center" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="text-gray-400 hover:text-[#14532D] transition-colors focus:outline-none"
        aria-label="More info"
      >
        <Info size={15} />
      </button>

      {open && (
        <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 z-50 bg-white border border-gray-200 shadow-md rounded-lg p-3 text-sm text-gray-700 leading-snug"
          style={{ maxWidth: 220, width: 'max-content' }}
        >
          {text}
          {/* Arrow */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-[5px] w-2.5 h-2.5 bg-white border-b border-r border-gray-200 rotate-45" />
        </div>
      )}
    </div>
  );
}
