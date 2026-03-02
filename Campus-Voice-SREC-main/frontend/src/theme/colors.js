// Single source of truth for SREC color tokens — mirrors tailwind.config.js srec.* keys
// Palette: Celadon #a1cca5 · Muted Teal #8fb996 · Muted Teal 2 #709775 · Hunter Green #415d43 · Carbon Black #111d13
export const SREC_COLORS = {
    // ── New palette ──────────────────────────────────────────────────────────
    celadon:     "#a1cca5",
    mutedTeal:   "#8fb996",
    mutedTeal2:  "#709775",
    hunterGreen: "#415d43",
    carbonBlack: "#111d13",

    // ── Token aliases ─────────────────────────────────────────────────────────
    primary:      "#415d43",   // Hunter Green
    primaryHover: "#111d13",   // Carbon Black
    primaryDark:  "#111d13",   // Carbon Black
    primaryLight: "#709775",   // Muted Teal 2
    primarySoft:  "#edf5ee",   // Very light celadon tint
    primaryMuted: "#8fb996",   // Muted Teal

    // Gold accents (unchanged)
    gold:      "#B8952E",
    goldLight: "#F5E2A0",
    goldMuted: "#D4B86A",

    // Backgrounds
    background:    "#f5faf5",
    backgroundAlt: "#edf5ee",
    card:          "#FFFFFF",
    cardHover:     "#f8fcf8",

    // Text hierarchy
    textPrimary:   "#111d13",   // Carbon Black
    textSecondary: "#415d43",   // Hunter Green
    textMuted:     "#709775",   // Muted Teal 2

    // Borders
    border:      "#c8deca",
    borderLight: "#ddeedd",
    borderHover: "#8fb996",

    // Semantic (unchanged)
    danger:      "#C82828",
    dangerLight: "#FEE2E2",
    dangerDark:  "#9B1C1C",
    warning:     "#D97706",
};

// Canonical status color map — shared between UI.jsx StatusBadge and AdminDashboard
export const STATUS_COLORS_HEX = {
    Raised:         { bg: '#EFF6FF', text: '#1D4ED8', border: '#DBEAFE', dot: '#60A5FA' },
    'In Progress':  { bg: '#FFFBEB', text: '#B45309', border: '#FDE68A', dot: '#FBBF24' },
    Resolved:       { bg: '#ECFDF5', text: '#065F46', border: '#A7F3D0', dot: '#10B981' },
    Closed:         { bg: '#F3F4F6', text: '#6B7280', border: '#E5E7EB', dot: '#9CA3AF' },
    Spam:           { bg: '#FEF2F2', text: '#B91C1C', border: '#FECACA', dot: '#F87171' },
};

// Chart palette — new green-earth tones
export const CHART_COLORS = [
    '#415d43',  // Hunter Green (primary)
    '#709775',  // Muted Teal 2
    '#8fb996',  // Muted Teal
    '#a1cca5',  // Celadon
    '#B8952E',  // SREC gold
    '#C82828',  // Deep crimson (danger/spam)
    '#6366F1',  // Indigo accent
    '#0EA5E9',  // Sky blue
    '#D97706',  // Amber
    '#111d13',  // Carbon Black (for dark bars)
];
