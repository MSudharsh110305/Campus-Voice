import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

export const ThemeContext = createContext({ theme: 'light', setTheme: () => {} });

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => {
    try {
      const saved = localStorage.getItem('cv_theme');
      return saved === 'neon' ? 'neon' : 'light';
    } catch {
      return 'light';
    }
  });

  // Stable reference — won't cause unnecessary re-renders
  const setTheme = useCallback((t) => {
    const valid = t === 'neon' ? 'neon' : 'light';
    setThemeState(valid);
    try { localStorage.setItem('cv_theme', valid); } catch {}
  }, []);

  useEffect(() => {
    const html = document.documentElement;
    if (theme === 'neon') {
      html.setAttribute('data-theme', 'neon');
      html.style.colorScheme = 'dark';
    } else {
      html.removeAttribute('data-theme');
      html.style.colorScheme = 'light';
    }
  }, [theme]);

  // Memoised value — children only re-render when theme actually changes
  const value = useMemo(() => ({ theme, setTheme }), [theme, setTheme]);

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => useContext(ThemeContext);
