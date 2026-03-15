import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useTheme } from '../context/ThemeContext';
import { Trophy, RotateCcw, X } from 'lucide-react';
import { api } from '../utils/api';

// ── Local cache helpers (offline fallback) ───────────────────────────────────
const LS_KEY = 'cv_dash_scores';
const LS_MY_KEY = 'cv_dash_me';

const getCached = () => {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter(e => e && typeof e.score === 'number') : [];
  } catch { return []; }
};

const setCached = (board) => {
  try { localStorage.setItem(LS_KEY, JSON.stringify(board)); } catch {}
};

// ── DB helpers ───────────────────────────────────────────────────────────────
const submitScoreDB = async (score) => {
  try { await api('/game/score', { method: 'POST', body: JSON.stringify({ score }) }); return true; }
  catch { return false; }
};

const fetchLeaderboard = async () => {
  try { return await api('/game/leaderboard'); }
  catch { return null; }
};

// ── Constants ────────────────────────────────────────────────────────────────
const CW = 680;
const CH = 190;
const GROUND = CH - 28;
const PH = 36;
const PW = 24;
const P_REST = GROUND - PH;

export default function OfflineGame({ onClose }) {
  const canvasRef = useRef(null);
  const stateRef = useRef(null);
  const rafRef   = useRef(null);
  const { theme } = useTheme();
  const isDark = theme === 'neon';

  const [phase, setPhase] = useState('idle');   // idle | playing | dead
  const [score, setScore] = useState(0);
  const [board, setBoard] = useState(getCached);
  const [myBestDB, setMyBestDB] = useState(() => { try { return JSON.parse(localStorage.getItem(LS_MY_KEY)) || null; } catch { return null; } });
  const [online, setOnline] = useState(navigator.onLine);

  const playerName = (() => {
    try { const u = JSON.parse(localStorage.getItem('user')); return u?.name?.split(' ')[0] || 'You'; }
    catch { return 'You'; }
  })();

  // Fetch leaderboard from DB on mount + when coming online
  useEffect(() => {
    const load = async () => {
      const data = await fetchLeaderboard();
      if (data) {
        setBoard(data.leaderboard || []);
        setCached(data.leaderboard || []);
        if (data.my_best != null) {
          setMyBestDB({ score: data.my_best, rank: data.my_rank });
          try { localStorage.setItem(LS_MY_KEY, JSON.stringify({ score: data.my_best, rank: data.my_rank })); } catch {}
        }
        setOnline(true);
      }
    };
    load();
    const onOnline = () => { setOnline(true); load(); };
    const onOffline = () => setOnline(false);
    window.addEventListener('online', onOnline);
    window.addEventListener('offline', onOffline);
    return () => { window.removeEventListener('online', onOnline); window.removeEventListener('offline', onOffline); };
  }, []);

  const C = isDark ? {
    bg: '#0d1117', groundFill: '#21262d', groundLine: '#3fb950',
    player: '#3fb950', eye: '#0d1117', cloud: '#161b22',
    obs: '#6e7681', obsAlt: '#3d444d',
    hudScore: '#3fb950', hudMuted: '#6e7681',
    text: '#e6edf3', sub: '#8b949e', border: '#30363d',
    cardBg: '#161b22', scoreBg: '#0d1117',
  } : {
    bg: '#f0fdf4', groundFill: '#dcfce7', groundLine: '#15803d',
    player: '#15803d', eye: '#fff', cloud: '#bbf7d0',
    obs: '#374151', obsAlt: '#9ca3af',
    hudScore: '#15803d', hudMuted: '#6b7280',
    text: '#111827', sub: '#4b5563', border: '#d1fae5',
    cardBg: '#ffffff', scoreBg: '#f0fdf4',
  };

  // ── Draw helpers ──────────────────────────────────────────────────────────
  const drawPlayer = (ctx, py, frame) => {
    const px = 70;
    const onG = py >= P_REST - 1;

    // shadow
    ctx.fillStyle = 'rgba(0,0,0,0.10)';
    ctx.beginPath();
    ctx.ellipse(px + PW / 2, GROUND + 5, 13, 4, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = C.player;
    // body
    ctx.beginPath(); ctx.roundRect(px, py + 14, PW, PH - 14, 4); ctx.fill();
    // head
    ctx.beginPath(); ctx.arc(px + PW / 2 + 2, py + 10, 10, 0, Math.PI * 2); ctx.fill();

    // whites of eye
    ctx.fillStyle = C.eye;
    ctx.beginPath(); ctx.arc(px + PW / 2 + 7, py + 8, 3.5, 0, Math.PI * 2); ctx.fill();
    // pupil
    ctx.fillStyle = '#111827';
    ctx.beginPath(); ctx.arc(px + PW / 2 + 8, py + 8, 2, 0, Math.PI * 2); ctx.fill();

    // mouth
    ctx.strokeStyle = C.eye; ctx.lineWidth = 1.5;
    ctx.beginPath();
    if (!onG) { ctx.arc(px + PW / 2 + 6, py + 13, 3.5, 0.1, Math.PI - 0.1); }
    else       { ctx.arc(px + PW / 2 + 6, py + 12, 3, 0.1, Math.PI - 0.1); }
    ctx.stroke();

    // legs
    ctx.fillStyle = C.player;
    const swing = onG ? Math.sin(frame * 0.22) * 7 : 0;
    ctx.beginPath(); ctx.roundRect(px + 3,       py + PH - 10, 7, 10 + swing,  3); ctx.fill();
    ctx.beginPath(); ctx.roundRect(px + PW - 10, py + PH - 10, 7, 10 - swing, 3); ctx.fill();
  };

  const drawObs = (ctx, o) => {
    ctx.save();
    ctx.fillStyle = C.obs;
    if (o.k === 0) {
      // stacked books
      for (let i = 0; i < 3; i++) {
        const bh = Math.floor(o.h / 3) - 1;
        ctx.beginPath(); ctx.roundRect(o.x + (i % 2) * 2, o.y + i * (bh + 2), o.w - (i % 2) * 4, bh, 2); ctx.fill();
        ctx.fillStyle = C.obsAlt;
        ctx.fillRect(o.x + 3, o.y + i * (bh + 2) + 3, o.w - 8, 2);
        ctx.fillStyle = C.obs;
      }
    } else if (o.k === 1) {
      // traffic cone
      ctx.beginPath();
      ctx.moveTo(o.x + o.w / 2, o.y);
      ctx.lineTo(o.x + o.w, o.y + o.h);
      ctx.lineTo(o.x, o.y + o.h);
      ctx.closePath(); ctx.fill();
      ctx.fillStyle = '#f59e0b';
      ctx.fillRect(o.x + o.w * 0.15, o.y + o.h * 0.52, o.w * 0.7, o.h * 0.14);
    } else {
      // bench
      ctx.beginPath(); ctx.roundRect(o.x, o.y, o.w, o.h * 0.38, 2); ctx.fill();
      ctx.fillRect(o.x + 3,       o.y + o.h * 0.35, 6, o.h * 0.65);
      ctx.fillRect(o.x + o.w - 9, o.y + o.h * 0.35, 6, o.h * 0.65);
    }
    ctx.restore();
  };

  // ── Start game ───────────────────────────────────────────────────────────
  const startGame = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    stateRef.current = {
      py: P_REST, vy: 0, jumps: 0,
      obstacles: [],
      clouds: [{ x: 180, y: 28, w: 72, h: 22, spd: 0.4 }, { x: 480, y: 18, w: 56, h: 18, spd: 0.25 }],
      score: 0, speed: 4, frame: 0, spawn: 90, gOff: 0, dead: false,
    };
    setScore(0);
    setPhase('playing');
  }, []);

  const doJump = useCallback(() => {
    const s = stateRef.current;
    if (!s || s.dead) return;
    if (s.jumps < 2) { s.vy = -12; s.jumps++; }
  }, []);

  // ── Input handling ───────────────────────────────────────────────────────
  useEffect(() => {
    const onKey = (e) => {
      if (e.code === 'Space' || e.code === 'ArrowUp') {
        e.preventDefault();
        if (phase === 'idle' || phase === 'dead') startGame();
        else doJump();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [phase, startGame, doJump]);

  // ── Game loop ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (phase !== 'playing') return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const s = stateRef.current;

    const TEMPLATES = [
      { w: 18, h: 40, k: 0 },
      { w: 20, h: 34, k: 1 },
      { w: 30, h: 26, k: 2 },
    ];

    const loop = () => {
      if (s.dead) return;
      s.frame++;
      s.score++;
      s.speed = 4 + Math.min(Math.floor(s.score / 350) * 0.5, 5);

      // Physics
      s.vy += 0.60;
      s.py = Math.min(s.py + s.vy, P_REST);
      if (s.py >= P_REST) { s.py = P_REST; s.vy = 0; s.jumps = 0; }

      // Clouds
      s.clouds.forEach(c => { c.x -= c.spd; if (c.x + c.w < 0) c.x = CW + c.w; });
      s.gOff = (s.gOff + s.speed) % 50;

      // Spawn
      s.spawn--;
      if (s.spawn <= 0) {
        const t = TEMPLATES[Math.floor(Math.random() * TEMPLATES.length)];
        s.obstacles.push({ x: CW + 10, y: GROUND - t.h, w: t.w, h: t.h, k: t.k });
        s.spawn = Math.max(45, Math.floor(70 + Math.random() * 65) - Math.floor(s.score / 600) * 5);
      }

      s.obstacles = s.obstacles.filter(o => o.x + o.w > -10);
      s.obstacles.forEach(o => { o.x -= s.speed; });

      // Collision (slightly forgiving hitbox)
      const pad = 5;
      for (const o of s.obstacles) {
        if (70 + pad < o.x + o.w && 70 + PW - pad > o.x &&
            s.py + pad < o.y + o.h && s.py + PH - pad > o.y) {
          s.dead = true;
          cancelAnimationFrame(rafRef.current);
          const finalScore = s.score;
          setScore(finalScore);
          setPhase('dead');
          // Save to DB + refresh leaderboard
          submitScoreDB(finalScore).then(async (saved) => {
            if (saved) {
              const data = await fetchLeaderboard();
              if (data) {
                setBoard(data.leaderboard || []);
                setCached(data.leaderboard || []);
                if (data.my_best != null) {
                  setMyBestDB({ score: data.my_best, rank: data.my_rank });
                  try { localStorage.setItem(LS_MY_KEY, JSON.stringify({ score: data.my_best, rank: data.my_rank })); } catch {}
                }
              }
            }
          });
          return;
        }
      }

      // ── Draw ──────────────────────────────────────────────────────────────
      ctx.fillStyle = C.bg;
      ctx.fillRect(0, 0, CW, CH);

      // Clouds
      ctx.fillStyle = C.cloud;
      s.clouds.forEach(c => {
        ctx.beginPath(); ctx.ellipse(c.x, c.y, c.w / 2, c.h / 2, 0, 0, Math.PI * 2); ctx.fill();
        ctx.beginPath(); ctx.ellipse(c.x - c.w * 0.25, c.y + 4, c.w * 0.28, c.h * 0.42, 0, 0, Math.PI * 2); ctx.fill();
        ctx.beginPath(); ctx.ellipse(c.x + c.w * 0.22, c.y + 5, c.w * 0.26, c.h * 0.40, 0, 0, Math.PI * 2); ctx.fill();
      });

      // Ground
      ctx.fillStyle = C.groundLine;
      ctx.fillRect(0, GROUND, CW, 2);
      ctx.fillStyle = C.groundFill;
      for (let x = -s.gOff; x < CW; x += 50) ctx.fillRect(x, GROUND + 4, 26, 2);

      drawPlayer(ctx, s.py, s.frame);
      s.obstacles.forEach(o => drawObs(ctx, o));

      // HUD
      const best = Math.max(getCached()[0]?.score ?? 0, s.score);
      ctx.textAlign = 'right';
      ctx.fillStyle = C.hudMuted;
      ctx.font = '11px monospace';
      ctx.fillText(`HI ${String(best).padStart(5, '0')}`, CW - 14, 20);
      ctx.fillStyle = C.hudScore;
      ctx.font = 'bold 16px monospace';
      ctx.fillText(String(s.score).padStart(5, '0'), CW - 14, 38);
      ctx.textAlign = 'left';

      rafRef.current = requestAnimationFrame(loop);
    };

    rafRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(rafRef.current);
  }, [phase]); // eslint-disable-line

  // ── Idle canvas (static scene) ────────────────────────────────────────────
  useEffect(() => {
    if (phase !== 'idle') return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = C.bg;
    ctx.fillRect(0, 0, CW, CH);
    ctx.fillStyle = C.groundLine;
    ctx.fillRect(0, GROUND, CW, 2);
    ctx.fillStyle = C.groundFill;
    for (let x = 0; x < CW; x += 50) ctx.fillRect(x, GROUND + 4, 26, 2);
    drawPlayer(ctx, P_REST, 0);
    ctx.fillStyle = C.hudMuted;
    ctx.font = '12px monospace';
    ctx.textAlign = 'center';
    ctx.fillText('tap to start', CW / 2, CH / 2 - 10);
    ctx.textAlign = 'left';
  }, [phase, isDark]); // eslint-disable-line

  // re-draw idle on theme change
  useEffect(() => {
    if (phase === 'idle') setPhase(p => p); // force idle redraw
  }, [isDark]); // eslint-disable-line

  const highScore = board[0]?.score ?? 0;
  const myBest = myBestDB?.score ?? 0;
  const myRank = myBestDB?.rank ?? null;

  return (
    <div className="fixed inset-0 z-[9998] flex flex-col"
      style={{ backgroundColor: C.cardBg }}>

      <div className="flex flex-col h-full w-full sm:items-center sm:justify-center sm:bg-black/60"
        style={{}}>
      <div className="flex flex-col h-full w-full sm:h-auto sm:max-w-2xl sm:rounded-2xl sm:overflow-hidden sm:shadow-2xl sm:border"
        style={{ backgroundColor: C.cardBg, borderColor: C.border }}>

        {/* Header */}
        <div className="px-4 pt-3 pb-2 border-b" style={{ borderColor: C.border }}>
          <div className="flex items-center justify-between">
            <h2 className="font-bold text-sm" style={{ color: C.text }}>Campus Dash</h2>
            {onClose && (
              <button onClick={onClose} className="p-1 rounded-lg hover:opacity-70 transition-opacity"
                style={{ color: C.sub }}>
                <X size={16} />
              </button>
            )}
          </div>

          {/* Stats row */}
          <div className="flex items-center gap-3 mt-2 flex-wrap">
            {/* Personal best + rank */}
            <div className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg"
              style={{ backgroundColor: isDark ? '#0d1117' : '#f0fdf4' }}>
              <Trophy size={11} style={{ color: C.hudScore }} />
              <span style={{ color: C.sub }}>Your best:</span>
              <span className="font-mono font-bold" style={{ color: C.hudScore }}>
                {myBest > 0 ? myBest : '—'}
              </span>
              {myRank > 0 && (
                <span className="font-semibold px-1.5 py-0.5 rounded text-[10px]"
                  style={{
                    backgroundColor: myRank === 1 ? '#f59e0b22' : isDark ? '#3fb95022' : '#15803d22',
                    color: myRank === 1 ? '#f59e0b' : C.hudScore,
                  }}>
                  #{myRank}
                </span>
              )}
            </div>

            {/* Global top scores */}
            {board.length > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-xs" style={{ color: C.sub }}>Top:</span>
                {board.slice(0, 5).map((s, i) => (
                  <span key={i} className="font-mono text-xs font-bold"
                    style={{ color: i === 0 ? '#f59e0b' : C.hudScore }}>
                    {s.score}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Canvas — scales width to container, aspect ratio maintained */}
        <div className="relative cursor-pointer select-none flex-1"
          onClick={() => { if (phase === 'idle' || phase === 'dead') startGame(); else doJump(); }}>
          <canvas ref={canvasRef} width={CW} height={CH}
            className="w-full block"
            style={{ touchAction: 'none' }} />

          {/* Dead overlay */}
          {phase === 'dead' && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2"
              style={{ backgroundColor: 'rgba(0,0,0,0.55)' }}>
              <p className="text-white font-bold text-lg">Game Over</p>
              <p className="text-white/70 text-sm">Score: <span className="font-bold text-white">{score}</span></p>
              {score >= highScore && score > 0 && (
                <p className="text-xs font-semibold px-3 py-1 rounded-full"
                  style={{ backgroundColor: C.hudScore, color: isDark ? '#0d1117' : '#fff' }}>
                  🏆 New high score!
                </p>
              )}
              <button onClick={(e) => { e.stopPropagation(); startGame(); }}
                className="mt-1 flex items-center gap-2 px-4 py-2 rounded-xl font-semibold text-sm"
                style={{ backgroundColor: C.player, color: isDark ? '#0d1117' : '#fff' }}>
                <RotateCcw size={14} /> Play Again
              </button>
            </div>
          )}
        </div>

      </div>
      </div>
    </div>
  );
}
