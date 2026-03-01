/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        srec: {
          // Core greens
          primary: "#14532D",
          primaryHover: "#166534",
          primaryLight: "#22C55E",
          primarySoft: "#DCFCE7",
          primaryMuted: "#86EFAC",

          // Gold accents
          gold: "#C8A135",
          goldLight: "#FDE68A",

          // Backgrounds — subtle green-tinted whites
          background: "#F7F9F7",
          backgroundAlt: "#F0F4F0",
          card: "#FFFFFF",
          cardHover: "#FCFDFB",

          // Text hierarchy
          textPrimary: "#0F1A0F",
          textSecondary: "#4B5E4B",
          textMuted: "#8A9B8A",

          // Borders — green-tinted grays
          border: "#E2E8E2",
          borderLight: "#EFF2EF",
          borderHover: "#C5D0C5",

          danger: "#EF4444",
          warning: "#F59E0B",
        },
        brand: {
          light: '#6ee7b7', // Soft Emerald 300
          DEFAULT: '#10b981', // Emerald 500 - Professional Green
          dark: '#047857', // Emerald 700
        },
        accent: {
          light: '#fde68a', // Amber 200 - Soft Gold highlight
          DEFAULT: '#d97706', // Amber 600 - Muted Gold
          dark: '#b45309', // Amber 700
        },
        background: '#f4f7f6', // Soft cool off-white for page background
        surface: '#ffffff', // Pure white for cards
        success: '#10b981', // Match brand
        error: '#f43f5e', // Soft Rose
        gray: {
          50: '#f9fafb',
          100: '#f3f4f6',
          200: '#e5e7eb',
          300: '#d1d5db',
          400: '#9ca3af',
          500: '#6b7280',
          600: '#4b5563',
          700: '#374151',
          800: '#1f2937',
          900: '#111827',
        },
        // Semantic Action Colors - Raise/Create
        raise: {
          light: '#fecaca',   // soft red for backgrounds
          DEFAULT: '#f87171', // coral red for actions
          dark: '#dc2626',    // darker red for text
        },
        // Priority Colors (pastel/mild)
        priority: {
          low: '#86efac',      // soft green
          medium: '#fcd34d',   // soft amber/yellow  
          high: '#fdba74',     // soft orange
          critical: '#fca5a5', // muted red
        },
        // Status Colors (pastel/mild)
        status: {
          raised: '#93c5fd',   // soft blue
          opened: '#5eead4',   // soft teal
          reviewed: '#c4b5fd', // soft violet
          closed: '#d1d5db',   // soft gray
        },
      },
      boxShadow: {
        // Refined layered shadows
        'soft': '0 1px 3px rgba(20,83,45,0.04), 0 1px 2px rgba(20,83,45,0.02)',
        'card': '0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02)',
        'card-hover': '0 4px 12px rgba(0,0,0,0.06), 0 2px 4px rgba(0,0,0,0.03)',
        'elevated': '0 8px 24px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.04)',
        'glow-green': '0 0 20px rgba(34,197,94,0.15)',
        'inner-soft': 'inset 0 1px 2px rgba(0,0,0,0.04)',
        // Neumorphic shadows
        'neu-flat': '0 2px 8px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02)',
        'neu-hover': '0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01)',
        'neu-pressed': 'inset 2px 2px 5px #e2e4e7, inset -2px -2px 5px #ffffff',
        'neu-light': '0 1px 2px rgba(0, 0, 0, 0.05)',
        'neu-inset': 'inset 3px 3px 6px #d1d5db, inset -3px -3px 6px #ffffff',
        'neu-raised': '6px 6px 12px #d1d5db, -6px -6px 12px #ffffff',
        'neu-soft': '4px 4px 8px #d1d5db, -4px -4px 8px #ffffff',
        // Raise button shadows
        'raise-btn': '0 4px 14px -2px rgba(248, 113, 113, 0.35), 0 2px 4px rgba(248, 113, 113, 0.2)',
        'raise-btn-hover': '0 8px 20px -2px rgba(248, 113, 113, 0.45), 0 4px 8px rgba(248, 113, 113, 0.25)',
        'raise-pressed': 'inset 0 2px 4px rgba(0,0,0,0.15)',
        // Vote button glow
        'vote-glow': '0 0 12px rgba(16, 185, 129, 0.4)',
        'vote-glow-down': '0 0 12px rgba(244, 63, 94, 0.4)',
      },
      keyframes: {
        'slide-up': {
          '0%': { transform: 'translateY(8px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'scale-in': {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
      animation: {
        'slide-up': 'slide-up 0.2s ease-out forwards',
        'scale-in': 'scale-in 0.15s ease-out forwards',
        'fade-in': 'fade-in 0.2s ease-out forwards',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
};

