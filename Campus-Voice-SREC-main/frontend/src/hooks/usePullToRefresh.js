import { useState, useRef, useCallback, useEffect } from 'react';

/**
 * Pull-to-refresh hook for mobile PWA.
 * Returns { pullRef, refreshing, pullProgress, handlers }
 * Attach handlers.onTouchStart/Move/End to the scrollable container.
 */
export default function usePullToRefresh(onRefresh, { threshold = 80, disabled = false } = {}) {
  const [refreshing, setRefreshing] = useState(false);
  const [pullDistance, setPullDistance] = useState(0);
  const startY = useRef(0);
  const pulling = useRef(false);

  const onTouchStart = useCallback((e) => {
    if (disabled || refreshing) return;
    // Only activate when scrolled to top
    const el = e.currentTarget;
    if (el.scrollTop > 5) return;
    startY.current = e.touches[0].clientY;
    pulling.current = true;
  }, [disabled, refreshing]);

  const onTouchMove = useCallback((e) => {
    if (!pulling.current || disabled || refreshing) return;
    const diff = e.touches[0].clientY - startY.current;
    if (diff < 0) { setPullDistance(0); return; }
    // Rubber-band effect: diminishing returns past threshold
    const damped = diff > threshold ? threshold + (diff - threshold) * 0.3 : diff;
    setPullDistance(damped);
  }, [disabled, refreshing, threshold]);

  const onTouchEnd = useCallback(async () => {
    if (!pulling.current) return;
    pulling.current = false;
    if (pullDistance >= threshold && onRefresh) {
      setRefreshing(true);
      try { await onRefresh(); } catch {}
      setRefreshing(false);
    }
    setPullDistance(0);
  }, [pullDistance, threshold, onRefresh]);

  const pullProgress = Math.min(1, pullDistance / threshold);

  return {
    refreshing,
    pullProgress,
    pullDistance,
    handlers: { onTouchStart, onTouchMove, onTouchEnd },
  };
}
