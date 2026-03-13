import React, { useEffect, useState } from 'react';

export default function ThemeToggle() {
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'light');

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') root.classList.add('dark'); else root.classList.remove('dark');
    localStorage.setItem('theme', theme);
  }, [theme]);

  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      aria-label="Toggle color theme"
      role="switch"
      aria-checked={isDark}
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
      className="fixed top-3 right-3 z-20 h-10 w-10 rounded-full bg-white/80 dark:bg-gray-800/80 border border-gray-200 dark:border-gray-700 shadow-md backdrop-blur flex items-center justify-center hover:shadow-lg transition"
    >
      <span className="text-gray-800 dark:text-gray-100 text-lg" aria-hidden>
        {isDark ? '☀️' : '🌙'}
      </span>
    </button>
  );
}





