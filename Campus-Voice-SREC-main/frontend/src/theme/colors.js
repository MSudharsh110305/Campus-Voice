// Single source of truth for SREC color tokens — mirrors tailwind.config.js srec.* keys
export const SREC_COLORS = {
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

    // Backgrounds
    background: "#F7F9F7",
    backgroundAlt: "#F0F4F0",
    card: "#FFFFFF",
    cardHover: "#FCFDFB",

    // Text hierarchy
    textPrimary: "#0F1A0F",
    textSecondary: "#4B5E4B",
    textMuted: "#8A9B8A",

    // Borders
    border: "#E2E8E2",
    borderLight: "#EFF2EF",
    borderHover: "#C5D0C5",

    // Semantic
    danger: "#C82828",
    dangerLight: "#FEE2E2",
    dangerDark: "#9B1C1C",
    warning: "#D97706",
};

// Canonical status color map — shared between UI.jsx StatusBadge and AdminDashboard
export const STATUS_COLORS_HEX = {
    Raised:       { bg: '#EFF6FF', text: '#1D4ED8', border: '#DBEAFE', dot: '#60A5FA' },
    'In Progress':{ bg: '#FFFBEB', text: '#B45309', border: '#FDE68A', dot: '#FBBF24' },
    Resolved:     { bg: '#ECFDF5', text: '#065F46', border: '#A7F3D0', dot: '#10B981' },
    Closed:       { bg: '#F3F4F6', text: '#6B7280', border: '#E5E7EB', dot: '#9CA3AF' },
    Spam:         { bg: '#FEF2F2', text: '#B91C1C', border: '#FECACA', dot: '#F87171' },
};

// Chart palette — derived from logo
export const CHART_COLORS = [
    '#14532D',  // SREC primary green
    '#B8952E',  // SREC gold
    '#22C55E',  // light green
    '#C82828',  // deep crimson
    '#6366F1',  // indigo accent
    '#0EA5E9',  // sky blue
    '#D97706',  // amber
];
