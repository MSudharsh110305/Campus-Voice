import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageSquare, Sparkles, CheckCircle2 } from 'lucide-react';

const slides = [
  {
    title: 'Raise Issues Easily',
    description: 'Report campus problems quickly with a clear complaint form.',
    icon: MessageSquare,
  },
  {
    title: 'AI Smart Routing',
    description: 'Your complaint is automatically analyzed and sent to the correct authority.',
    icon: Sparkles,
  },
  {
    title: 'Track & Resolve',
    description: 'Track complaint status and get updates when action is taken.',
    icon: CheckCircle2,
  },
];

export default function Onboarding() {
  const navigate = useNavigate();
  const [idx, setIdx] = useState(0);
  const isLast = useMemo(() => idx === slides.length - 1, [idx]);

  const next = () => {
    if (isLast) {
      localStorage.setItem('onboarded', 'true');
      localStorage.removeItem('cv_last_tab');
      navigate('/login');
    } else {
      setIdx((i) => Math.min(i + 1, slides.length - 1));
    }
  };

  const skip = () => {
    localStorage.setItem('onboarded', 'true');
    localStorage.removeItem('cv_last_tab');
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-[#F8FAF8] flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-3xl rounded-2xl shadow-lg bg-white p-10 border border-[#E5E7EB] flex flex-col items-center">
        
        {/* Header */}
        <div className="text-center w-full mb-12">
          <h1 className="font-bold text-xl text-[#14532D]">CampusVoice</h1>
          <p className="text-sm text-gray-500 font-medium">Smart Campus Complaint System</p>
        </div>

        {/* Slider Content */}
        <div className="w-full flex-grow flex flex-col items-center justify-center min-h-[300px]">
          <AnimatePresence mode="wait">
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.4 }}
              className="flex flex-col items-center text-center max-w-md w-full"
            >
              <div className="relative mb-8 flex justify-center items-center">
                {/* Illustration Backdrop */}
                <div className="absolute w-32 h-32 bg-green-100 blur-3xl opacity-40 rounded-full" />
                
                {/* Icon */}
                <div className="w-20 h-20 text-[#14532D] bg-green-50 rounded-full p-4 relative z-10 flex items-center justify-center">
                  {React.createElement(slides[idx].icon, { className: 'w-full h-full stroke-[1.5]' })}
                </div>
              </div>

              <h2 className="text-2xl sm:text-3xl font-bold text-[#111827] mb-3">
                {slides[idx].title}
              </h2>
              <p className="text-[#6B7280] text-base sm:text-lg">
                {slides[idx].description}
              </p>
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Step Progress Indicator */}
        <div className="flex items-center justify-center gap-2 mt-10 mb-8 w-full">
          {slides.map((_, i) => (
            <span
              key={i}
              className={`h-2.5 rounded-full transition-all duration-300 ${
                i === idx ? 'w-8 bg-[#14532D]' : 'w-2.5 bg-gray-300'
              }`}
            />
          ))}
        </div>

        {/* Actions */}
        <div className="w-full flex flex-col items-center gap-4 max-w-xs">
          <button
            onClick={next}
            className="w-full bg-[#14532D] hover:bg-[#166534] text-white rounded-xl px-6 py-3 font-semibold transition-colors duration-200"
          >
            {isLast ? 'Get Started' : 'Next'}
          </button>
          
          <button
            onClick={skip}
            className="text-gray-500 hover:text-[#14532D] font-medium transition-colors"
          >
            Skip
          </button>
        </div>

      </div>
    </div>
  );
}
