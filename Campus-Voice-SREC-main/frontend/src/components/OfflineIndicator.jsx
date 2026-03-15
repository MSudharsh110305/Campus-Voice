import React, { useState, useEffect, useRef } from 'react';
import { WifiOff, Loader2, CheckCircle, Gamepad2, ServerCrash } from 'lucide-react';
import { getPendingComplaints, deletePendingComplaint } from '../utils/idb';
import { tokenStorage } from '../utils/api';
import OfflineGame from './OfflineGame';

// ── Pending game-score queue (localStorage) ──────────────────────────────────
// When the game is played offline, the score is saved here.
// On reconnect, we sync it to the server so the leaderboard stays current.
const PENDING_SCORE_KEY = 'cv_pending_game_score';

export function savePendingScore(score, coins) {
  try {
    const existing = JSON.parse(localStorage.getItem(PENDING_SCORE_KEY) || 'null');
    // Keep only the best pending score to avoid inflating leaderboard
    if (!existing || score > existing.score) {
      localStorage.setItem(PENDING_SCORE_KEY, JSON.stringify({ score, coins }));
    }
  } catch {}
}

async function syncPendingScore() {
  try {
    const pending = JSON.parse(localStorage.getItem(PENDING_SCORE_KEY) || 'null');
    if (!pending) return;
    const token = tokenStorage.getAccessToken();
    if (!token) return;
    const res = await fetch('/api/game/score', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ score: pending.score, coins_earned: pending.coins }),
    });
    if (res.ok) localStorage.removeItem(PENDING_SCORE_KEY);
  } catch {}
}

// ── Server reachability probe ─────────────────────────────────────────────────
async function isServerReachable() {
  try {
    const res = await fetch('/api/health', { method: 'GET', cache: 'no-store',
      signal: AbortSignal.timeout(4000) });
    return res.ok || res.status < 500;
  } catch {
    return false;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
export default function OfflineIndicator() {
  const [isOnline, setIsOnline]         = useState(navigator.onLine);
  const [serverDown, setServerDown]     = useState(false);
  const [syncing, setSyncing]           = useState(false);
  const [pendingCount, setPendingCount] = useState(0);
  const [justSynced, setJustSynced]     = useState(false);
  const [showGame, setShowGame]         = useState(false);
  const probeRef                        = useRef(null);

  // Probe the server every 30s when online to detect "server unreachable" state
  const startProbing = () => {
    stopProbing();
    probeRef.current = setInterval(async () => {
      if (!navigator.onLine) return;
      const ok = await isServerReachable();
      setServerDown(!ok);
    }, 30_000);
  };
  const stopProbing = () => { if (probeRef.current) clearInterval(probeRef.current); };

  useEffect(() => {
    const handleOnline = async () => {
      setIsOnline(true);
      // Sync pending game score first (no auth barrier)
      syncPendingScore();
      // Then sync offline complaints
      const pending = await getPendingComplaints().catch(() => []);
      if (pending.length > 0) {
        setPendingCount(pending.length);
        await submitPending(pending);
      }
      // Re-probe server immediately
      const ok = await isServerReachable();
      setServerDown(!ok);
      startProbing();
    };
    const handleOffline = () => {
      setIsOnline(false);
      setJustSynced(false);
      setServerDown(false);
      stopProbing();
    };

    window.addEventListener('online',  handleOnline);
    window.addEventListener('offline', handleOffline);

    // Initial setup
    getPendingComplaints().then(p => setPendingCount(p.length)).catch(() => {});
    if (navigator.onLine) {
      isServerReachable().then(ok => setServerDown(!ok));
      startProbing();
    }

    return () => {
      window.removeEventListener('online',  handleOnline);
      window.removeEventListener('offline', handleOffline);
      stopProbing();
    };
  }, []); // eslint-disable-line

  const submitPending = async (pending) => {
    setSyncing(true);
    const token = tokenStorage.getAccessToken();
    let submitted = 0;
    for (const item of pending) {
      try {
        const fd = new FormData();
        fd.append('original_text', item.original_text);
        fd.append('visibility', item.visibility || 'Public');
        fd.append('is_anonymous', 'true');
        const res = await fetch('/api/complaints/submit', {
          method: 'POST',
          headers: { Authorization: `Bearer ${token || item.access_token || ''}` },
          body: fd,
        });
        if (res.ok) {
          await deletePendingComplaint(item.id);
          submitted++;
          setPendingCount(c => Math.max(0, c - 1));
        }
      } catch { /* still down, retry later */ }
    }
    setSyncing(false);
    if (submitted > 0) {
      setJustSynced(true);
      setPendingCount(0);
      setTimeout(() => setJustSynced(false), 3000);
    }
  };

  // Nothing to show
  if (isOnline && !serverDown && !syncing && !justSynced) return null;

  const isOffline    = !isOnline;
  const isUnreachable = isOnline && serverDown;

  const bgClass = justSynced
    ? 'bg-emerald-600'
    : syncing
    ? 'bg-blue-600'
    : isUnreachable
    ? 'bg-amber-600'
    : 'bg-gray-900'; // offline

  return (
    <>
      <div
        className={`fixed top-0 left-0 right-0 z-[9999] flex items-center justify-center gap-2 py-2 px-4 text-xs font-medium text-white transition-all ${bgClass}`}
      >
        {isOffline && (
          <>
            <WifiOff size={13} />
            <span>Offline — scores cached locally, syncs on reconnect</span>
            <button
              onClick={() => setShowGame(true)}
              className="ml-2 flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-white/20 hover:bg-white/30 transition-colors text-white text-xs font-semibold"
            >
              <Gamepad2 size={11} /> Play Campus Dash
            </button>
          </>
        )}
        {isUnreachable && (
          <>
            <ServerCrash size={13} />
            <span>Server unreachable — playing Campus Dash? It works fully offline!</span>
            <button
              onClick={() => setShowGame(true)}
              className="ml-2 flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-white/20 hover:bg-white/30 transition-colors text-white text-xs font-semibold"
            >
              <Gamepad2 size={11} /> Play
            </button>
          </>
        )}
        {syncing && (
          <><Loader2 size={13} className="animate-spin" /> Syncing {pendingCount} queued complaint{pendingCount !== 1 ? 's' : ''}…</>
        )}
        {justSynced && (
          <><CheckCircle size={13} /> Queued complaints submitted!</>
        )}
      </div>

      {showGame && <OfflineGame onClose={() => setShowGame(false)} />}
    </>
  );
}
