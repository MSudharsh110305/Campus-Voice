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
          // Core greens — SREC logo palette
          primary: "#14532D",
          primaryHover: "#155D31",
          primaryLight: "#22C55E",
          primarySoft: "#DCFCE7",
          primaryMuted: "#86EFAC",

          // Gold accents — warm logo gold
          gold: "#B8952E",
          goldLight: "#F5E2A0",
          goldMuted: "#D4B86A",

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

          // Danger — deep warm crimson (replaces flat bright red)
          danger: "#C82828",
          dangerLight: "#FEE2E2",
          dangerDark: "#9B1C1C",
          warning: "#D97706",
        },
        brand: {
          light: '#6ee7b7',
          DEFAULT: '#10b981',
          dark: '#047857',
        },
        accent: {
          light: '#f5e2a0',
          DEFAULT: '#B8952E',
          dark: '#8B6F1E',
        },
        background: '#F7F9F7',
        surface: '#ffffff',
        success: '#10b981',
        error: '#C82828',
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
        // Raise button — slightly deeper warm coral
        raise: {
          light: '#fde8e8',
          DEFAULT: '#D95555',
          dark: '#B91C1C',
        },
        // Priority Colors
        priority: {
          low: '#86efac',
          medium: '#fcd34d',
          high: '#fdba74',
          critical: '#fca5a5',
        },
        // Status Colors
        status: {
          raised: '#93c5fd',
          opened: '#5eead4',
          reviewed: '#c4b5fd',
          closed: '#d1d5db',
        },
      },
      boxShadow: {
        // Refined layered shadows
        'soft': '0 1px 3px rgba(20,83,45,0.06), 0 1px 2px rgba(20,83,45,0.04)',
        'card': '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
        'card-hover': '0 4px 14px rgba(0,0,0,0.08), 0 2px 6px rgba(0,0,0,0.04)',
        'elevated': '0 8px 24px rgba(0,0,0,0.10), 0 2px 8px rgba(0,0,0,0.06)',
        'glow-green': '0 0 20px rgba(34,197,94,0.18)',
        'inner-soft': 'inset 0 1px 3px rgba(0,0,0,0.06)',
        // Button depth shadows — key addition
        'btn': '0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.08)',
        'btn-hover': '0 4px 10px rgba(0,0,0,0.14), 0 2px 4px rgba(0,0,0,0.08)',
        'btn-primary': '0 2px 6px rgba(20,83,45,0.30), 0 1px 3px rgba(20,83,45,0.20)',
        'btn-primary-hover': '0 4px 14px rgba(20,83,45,0.35), 0 2px 6px rgba(20,83,45,0.20)',
        'btn-danger': '0 2px 6px rgba(200,40,40,0.28), 0 1px 3px rgba(200,40,40,0.16)',
        'btn-danger-hover': '0 4px 12px rgba(200,40,40,0.35), 0 2px 4px rgba(200,40,40,0.18)',
        // Neumorphic shadows
        'neu-flat': '0 2px 8px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02)',
        'neu-hover': '0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01)',
        'neu-pressed': 'inset 2px 2px 5px #e2e4e7, inset -2px -2px 5px #ffffff',
        'neu-light': '0 1px 2px rgba(0, 0, 0, 0.05)',
        'neu-inset': 'inset 3px 3px 6px #d1d5db, inset -3px -3px 6px #ffffff',
        'neu-raised': '6px 6px 12px #d1d5db, -6px -6px 12px #ffffff',
        'neu-soft': '4px 4px 8px #d1d5db, -4px -4px 8px #ffffff',
        // Raise button shadows
        'raise-btn': '0 4px 14px -2px rgba(217,85,85,0.40), 0 2px 4px rgba(217,85,85,0.22)',
        'raise-btn-hover': '0 8px 22px -2px rgba(217,85,85,0.50), 0 4px 8px rgba(217,85,85,0.28)',
        'raise-pressed': 'inset 0 2px 4px rgba(0,0,0,0.18)',
        // Vote button glow
        'vote-glow': '0 0 12px rgba(16, 185, 129, 0.4)',
        'vote-glow-down': '0 0 12px rgba(200, 40, 40, 0.35)',
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
        sans: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', 'sans-serif'],
      },
      letterSpacing: {
        tightest: '-0.04em',
        tighter: '-0.02em',
      },
    },
  },
  plugins: [],
};
