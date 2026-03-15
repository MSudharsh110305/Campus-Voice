import React, { useEffect, useLayoutEffect, useRef, useState, useCallback } from 'react';
import { useTheme } from '../context/ThemeContext';
import { Trophy, RotateCcw, X, ShoppingBag } from 'lucide-react';
import { api } from '../utils/api';

// ── Skins (sprite-backed) ──────────────────────────────────────────────────────
const SKINS = [
  { id: 'default', name: 'Dude',    spriteBase: 'dude',    idleFrames: 4, runFrames: 6, jumpFrames: 8, color: '#3b82f6', lightColor: '#2563eb', price: 0   },
  { id: 'blue',    name: 'Pink',    spriteBase: 'pink',    idleFrames: 4, runFrames: 6, jumpFrames: 8, color: '#ec4899', lightColor: '#db2777', price: 100 },
  { id: 'purple',  name: 'Owlet',   spriteBase: 'owlet',   idleFrames: 4, runFrames: 6, jumpFrames: 8, color: '#6366f1', lightColor: '#4f46e5', price: 250 },
  { id: 'gold',    name: 'Shinobi', spriteBase: 'shinobi', idleFrames: 6, runFrames: 8, jumpFrames: 12, color: '#f59e0b', lightColor: '#d97706', price: 500 },
];

// ── Per-user localStorage keys ────────────────────────────────────────────────
const LS_KEY = 'cv_dash_scores';
const getRollNo = () => {
  try { const u = JSON.parse(localStorage.getItem('user')); return u?.roll_no || 'guest'; }
  catch { return 'guest'; }
};
const lsMyKey    = () => `cv_dash_me_${getRollNo()}`;
const lsCoinsKey = () => `cv_dash_coins_${getRollNo()}`;
const lsSkinKey  = () => `cv_dash_skin_${getRollNo()}`;
const lsOwnedKey = () => `cv_dash_owned_${getRollNo()}`;

const getCached = () => {
  try {
    const p = JSON.parse(localStorage.getItem(LS_KEY) || '[]');
    return Array.isArray(p) ? p.filter(e => e?.score != null) : [];
  } catch { return []; }
};
const setCached = (b) => { try { localStorage.setItem(LS_KEY, JSON.stringify(b)); } catch {} };

// ── DB helpers ────────────────────────────────────────────────────────────────
const submitScoreDB = async (score, coinsEarned) => {
  try {
    await api('/game/score', { method: 'POST', body: JSON.stringify({ score, coins_earned: coinsEarned }) });
    return true;
  } catch { return false; }
};
const fetchLeaderboard = async () => {
  try { return await api('/game/leaderboard'); } catch { return null; }
};
const spendCoinsDB = async (amount) => {
  try { await api('/game/spend-coins', { method: 'POST', body: JSON.stringify({ amount }) }); } catch {}
};

// ── Sprite helpers ─────────────────────────────────────────────────────────────
function removeWhiteBg(img) {
  try {
    const oc = new OffscreenCanvas(img.width, img.height);
    const ctx = oc.getContext('2d');
    ctx.drawImage(img, 0, 0);
    const id = ctx.getImageData(0, 0, img.width, img.height);
    const d = id.data;
    for (let i = 0; i < d.length; i += 4) {
      if (d[i] > 215 && d[i + 1] > 215 && d[i + 2] > 215) d[i + 3] = 0;
    }
    ctx.putImageData(id, 0, 0);
    return oc;
  } catch { return img; }
}

// ── Fallback player draw (used when sprites not yet loaded) ───────────────────
function drawFallbackPlayer(ctx, px, py, PW, PH, frame, color, isDark, GROUND) {
  const onGround = py >= GROUND - PH - 2;
  ctx.fillStyle = 'rgba(0,0,0,0.12)';
  ctx.beginPath();
  ctx.ellipse(px + PW / 2, GROUND + 4, PW * 0.65, 3.5, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = color;
  ctx.beginPath(); ctx.roundRect(px, py + PH * 0.38, PW, PH * 0.62, 3); ctx.fill();
  ctx.beginPath(); ctx.arc(px + PW * 0.55, py + PH * 0.24, PW * 0.46, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = isDark ? '#0d1117' : '#ffffff';
  ctx.beginPath(); ctx.arc(px + PW * 0.78, py + PH * 0.19, PW * 0.14, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#111827';
  ctx.beginPath(); ctx.arc(px + PW * 0.81, py + PH * 0.19, PW * 0.085, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = isDark ? '#0d1117' : '#ffffff';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.arc(px + PW * 0.72, py + PH * 0.33, PW * 0.16, 0.1, Math.PI - 0.1);
  ctx.stroke();
  ctx.fillStyle = color;
  const swing = onGround ? Math.sin(frame * 0.22) * PH * 0.12 : 0;
  ctx.beginPath(); ctx.roundRect(px + PW * 0.12, py + PH * 0.77, PW * 0.28, PH * 0.23 + swing, 2); ctx.fill();
  ctx.beginPath(); ctx.roundRect(px + PW * 0.55, py + PH * 0.77, PW * 0.28, PH * 0.23 - swing, 2); ctx.fill();
}

function drawObstacle(ctx, o, isDark) {
  ctx.save();
  if (o.k === 0) {
    const cols = isDark ? ['#1f6feb', '#3fb950', '#e67e22'] : ['#1565c0', '#2e7d32', '#f57c00'];
    for (let i = 0; i < 3; i++) {
      const bh = Math.floor(o.h / 3) - 1;
      ctx.fillStyle = cols[i];
      ctx.beginPath(); ctx.roundRect(o.x + (i % 2) * 2, o.y + i * (bh + 2), o.w - (i % 2) * 4, bh, 2); ctx.fill();
      ctx.fillStyle = 'rgba(255,255,255,0.2)';
      ctx.fillRect(o.x + 3, o.y + i * (bh + 2) + 3, o.w - 8, 2);
    }
  } else if (o.k === 1) {
    ctx.fillStyle = isDark ? '#e67e22' : '#f57c00';
    ctx.beginPath();
    ctx.moveTo(o.x + o.w / 2, o.y);
    ctx.lineTo(o.x + o.w, o.y + o.h);
    ctx.lineTo(o.x, o.y + o.h);
    ctx.closePath(); ctx.fill();
    ctx.fillStyle = 'rgba(255,255,255,0.45)';
    ctx.fillRect(o.x + o.w * 0.15, o.y + o.h * 0.52, o.w * 0.7, o.h * 0.13);
    ctx.fillRect(o.x + o.w * 0.25, o.y + o.h * 0.72, o.w * 0.5, o.h * 0.1);
  } else {
    ctx.fillStyle = isDark ? '#966c3a' : '#795548';
    ctx.beginPath(); ctx.roundRect(o.x, o.y, o.w, o.h * 0.38, 2); ctx.fill();
    ctx.fillStyle = isDark ? '#7a5230' : '#5d4037';
    ctx.fillRect(o.x + 3, o.y + o.h * 0.36, o.w * 0.22, o.h * 0.64);
    ctx.fillRect(o.x + o.w - o.w * 0.22 - 3, o.y + o.h * 0.36, o.w * 0.22, o.h * 0.64);
  }
  ctx.restore();
}

// ── SkinPreview: canvas showing the first idle frame of a sprite ───────────────
function SkinPreview({ spriteBase, frameCount, size = 52 }) {
  const ref = useRef(null);
  useEffect(() => {
    const img = new Image();
    let alive = true;
    img.onload = () => {
      if (!alive || !ref.current) return;
      const fw = Math.floor(img.width / frameCount);
      const ctx = ref.current.getContext('2d');
      ctx.clearRect(0, 0, size, size);
      ctx.imageSmoothingEnabled = false;
      if (spriteBase === 'shinobi') {
        const processed = removeWhiteBg(img);
        ctx.drawImage(processed, 0, 0, fw, img.height, 0, 0, size, size);
      } else {
        ctx.drawImage(img, 0, 0, fw, img.height, 0, 0, size, size);
      }
    };
    img.src = `/sprites/${spriteBase}_idle.png`;
    return () => { alive = false; };
  }, [spriteBase, frameCount, size]);
  return (
    <canvas
      ref={ref}
      width={size}
      height={size}
      style={{ imageRendering: 'pixelated', display: 'block' }}
    />
  );
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function OfflineGame({ onClose }) {
  const { theme } = useTheme();
  const isDark = theme === 'neon';
  const canvasRef    = useRef(null);
  const containerRef = useRef(null);
  const stateRef     = useRef(null);
  const rafRef       = useRef(null);
  const cvsSizeRef   = useRef({ w: 800, h: 320 });
  const spritesRef   = useRef({});
  const [spritesReady, setSpritesReady] = useState(false);

  const [phase, setPhase]               = useState('idle');
  const [score, setScore]               = useState(0);
  const [coinsThisRun, setCoinsThisRun] = useState(0);
  const [cvsVersion, setCvsVersion]     = useState(0);
  const [showShop, setShowShop]         = useState(false);
  const [shopMsg, setShopMsg]           = useState('');

  // Per-user state
  const [board, setBoard] = useState(getCached);
  const [myBestDB, setMyBestDB] = useState(() => {
    try { return JSON.parse(localStorage.getItem(lsMyKey())) || null; } catch { return null; }
  });
  const [myCoins, setMyCoins] = useState(() => {
    try { return parseInt(localStorage.getItem(lsCoinsKey()) || '0', 10); } catch { return 0; }
  });
  const [equippedSkin, setEquippedSkin] = useState(() => {
    try { return localStorage.getItem(lsSkinKey()) || 'default'; } catch { return 'default'; }
  });
  const [ownedSkins, setOwnedSkins] = useState(() => {
    try { return JSON.parse(localStorage.getItem(lsOwnedKey()) || '["default"]'); } catch { return ['default']; }
  });

  const skinObj   = SKINS.find(s => s.id === equippedSkin) || SKINS[0];
  const skinColor = isDark ? skinObj.color : skinObj.lightColor;

  const C = {
    skyTop:    isDark ? '#0d1117' : '#bbdefb',
    skyBot:    isDark ? '#0f1923' : '#e3f2fd',
    groundTop: isDark ? '#21262d' : '#a5d6a7',
    groundBot: isDark ? '#0d1117' : '#81c784',
    groundLine: isDark ? '#3fb950' : '#2e7d32',
    groundDash: isDark ? '#30363d' : '#c8e6c9',
    cloud:     isDark ? 'rgba(33,38,45,0.8)' : 'rgba(255,255,255,0.85)',
    hudScore:  isDark ? '#3fb950' : '#1b5e20',
    hudMuted:  isDark ? '#6e7681' : '#78909c',
    text:      isDark ? '#e6edf3' : '#111827',
    sub:       isDark ? '#8b949e' : '#4b5563',
    border:    isDark ? '#30363d' : '#a5d6a7',
    cardBg:    isDark ? '#161b22' : '#ffffff',
    headerBg:  isDark ? '#0d1117' : '#f0fdf4',
    overlay:   isDark ? 'rgba(0,0,0,0.65)' : 'rgba(0,0,0,0.5)',
    player: skinColor,
  };

  // ── Load all sprites once ──────────────────────────────────────────────────
  useEffect(() => {
    const entries = [
      ['dude_run',    6], ['dude_jump',    8], ['dude_idle',    4],
      ['pink_run',    6], ['pink_jump',    8], ['pink_idle',    4],
      ['owlet_run',   6], ['owlet_jump',   8], ['owlet_idle',   4],
      ['shinobi_run', 8], ['shinobi_jump', 12], ['shinobi_idle', 6],
    ];
    let loaded = 0;
    entries.forEach(([key, frames]) => {
      const img = new Image();
      img.onload = () => {
        const frameW = Math.floor(img.width / frames);
        const frameH = img.height;
        const isShinobi = key.startsWith('shinobi');
        const src = isShinobi ? removeWhiteBg(img) : img;
        spritesRef.current[key] = { img: src, frames, frameW, frameH };
        loaded++;
        if (loaded === entries.length) setSpritesReady(true);
      };
      img.onerror = () => {
        loaded++;
        if (loaded === entries.length) setSpritesReady(true);
      };
      img.src = `/sprites/${key}.png`;
    });
  }, []);

  // ── Fetch leaderboard on mount / reconnect ─────────────────────────────────
  useEffect(() => {
    const load = async () => {
      const data = await fetchLeaderboard();
      if (!data) return;
      setBoard(data.leaderboard || []);
      setCached(data.leaderboard || []);
      if (data.my_best != null) {
        const me = { score: data.my_best, rank: data.my_rank };
        setMyBestDB(me);
        try { localStorage.setItem(lsMyKey(), JSON.stringify(me)); } catch {}
      }
      if (data.my_coins != null) {
        setMyCoins(data.my_coins);
        try { localStorage.setItem(lsCoinsKey(), String(data.my_coins)); } catch {}
      }
    };
    load();
    window.addEventListener('online', load);
    return () => window.removeEventListener('online', load);
  }, []);

  // ── Canvas resize observer ─────────────────────────────────────────────────
  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver(([entry]) => {
      const w = Math.max(200, Math.floor(entry.contentRect.width));
      const h = Math.max(120, Math.floor(entry.contentRect.height));
      cvsSizeRef.current = { w, h };
      if (canvasRef.current) {
        canvasRef.current.width = w;
        canvasRef.current.height = h;
      }
      setCvsVersion(v => v + 1);
      setPhase(prev => (prev === 'playing' ? 'idle' : prev));
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  // ── Start game ─────────────────────────────────────────────────────────────
  const startGame = useCallback(() => {
    if (showShop) return;
    cancelAnimationFrame(rafRef.current);
    const canvas = canvasRef.current;
    const CW = canvas?.width  || cvsSizeRef.current.w;
    const CH = canvas?.height || cvsSizeRef.current.h;
    const GROUND   = CH - Math.max(28, CH * 0.11);
    const PH       = Math.max(28, CW * 0.048);
    const PW       = Math.max(18, CW * 0.034);
    const PLAYER_X = Math.max(55, CW * 0.085);
    stateRef.current = {
      py: GROUND - PH, vy: 0, jumps: 0,
      obstacles: [], coins: [],
      clouds: [
        { x: CW * 0.28, y: CH * 0.10, w: CW * 0.11, h: CH * 0.07,  spd: 0.5  },
        { x: CW * 0.72, y: CH * 0.07, w: CW * 0.08, h: CH * 0.055, spd: 0.28 },
        { x: CW * 0.50, y: CH * 0.14, w: CW * 0.07, h: CH * 0.05,  spd: 0.35 },
      ],
      score: 0, speed: CW * 0.006,
      frame: 0, spawn: 80, gOff: 0, dead: false,
      coinsCollected: 0,
      PH, PW, PLAYER_X, GROUND, CW, CH,
    };
    setScore(0);
    setCoinsThisRun(0);
    setPhase('playing');
  }, [showShop]);

  const doJump = useCallback(() => {
    const s = stateRef.current;
    if (!s || s.dead) return;
    if (s.jumps < 2) { s.vy = -(s.CH * 0.056 + 2); s.jumps++; }
  }, []);

  // ── Keyboard input ─────────────────────────────────────────────────────────
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

  // ── Game loop ──────────────────────────────────────────────────────────────
  useEffect(() => {
    if (phase !== 'playing') return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const s   = stateRef.current;
    const _isDark    = isDark;
    const _C         = { ...C };
    const _skinBase  = skinObj.spriteBase;
    const _skinColor = skinColor;

    const loop = () => {
      if (s.dead) return;
      s.frame++;

      // Score: +1 every 3 frames ≈ 20 pts/sec
      if (s.frame % 3 === 0) s.score++;

      // Speed ramp
      s.speed = s.CW * 0.006 + Math.min(Math.floor(s.score / 150) * s.CW * 0.0008, s.CW * 0.009);

      // Physics
      s.vy += s.CH * 0.0025;
      s.py = Math.min(s.py + s.vy, s.GROUND - s.PH);
      if (s.py >= s.GROUND - s.PH) { s.py = s.GROUND - s.PH; s.vy = 0; s.jumps = 0; }

      // Clouds
      s.clouds.forEach(c => { c.x -= c.spd; if (c.x + c.w < 0) c.x = s.CW + c.w; });
      s.gOff = (s.gOff + s.speed) % 50;

      // Spawn obstacles
      s.spawn--;
      if (s.spawn <= 0) {
        const sizes = [
          { w: s.CW * 0.026, h: s.CW * 0.058, k: 0 },
          { w: s.CW * 0.030, h: s.CW * 0.050, k: 1 },
          { w: s.CW * 0.044, h: s.CW * 0.038, k: 2 },
        ];
        const t = sizes[Math.floor(Math.random() * sizes.length)];
        s.obstacles.push({ x: s.CW + 10, y: s.GROUND - t.h, w: t.w, h: t.h, k: t.k });
        s.spawn = Math.max(42, Math.floor(72 + Math.random() * 62) - Math.floor(s.score / 300) * 5);

        // Spawn coin trail AFTER the obstacle (easy single-jump height)
        if (Math.random() < 0.4) {
          const count = 1 + Math.floor(Math.random() * 3); // 1–3 coins in a trail
          // Place coins well after the obstacle so the player has cleared it before reaching them
          const startX = s.CW + t.w + s.CW * 0.10;
          // Comfortable single-jump arc: 20-30% of jump height above ground
          const jumpH = s.CH * 0.32;
          const coinY = s.GROUND - s.PH - jumpH * (0.20 + Math.random() * 0.18);
          const safeY = Math.max(s.GROUND * 0.30, coinY);
          for (let ci = 0; ci < count; ci++) {
            s.coins.push({
              x: startX + ci * s.CW * 0.035,
              y: safeY,
              r: Math.max(6, s.CW * 0.012),
              collected: false,
            });
          }
        }
      }

      // Move obstacles + coins
      s.obstacles = s.obstacles.filter(o => o.x + o.w > -10);
      s.obstacles.forEach(o => { o.x -= s.speed; });
      s.coins = s.coins.filter(c => !c.collected && c.x > -20);
      s.coins.forEach(c => { c.x -= s.speed; });

      // Coin collection
      const pcx = s.PLAYER_X + s.PW * 0.5;
      const pcy = s.py + s.PH * 0.5;
      s.coins.forEach(c => {
        if (c.collected) return;
        if (Math.hypot(pcx - c.x, pcy - c.y) < c.r + s.PW * 0.55) {
          c.collected = true;
          s.coinsCollected++;
          setCoinsThisRun(s.coinsCollected);
        }
      });

      // Collision
      const pad = 4;
      for (const o of s.obstacles) {
        if (s.PLAYER_X + pad < o.x + o.w && s.PLAYER_X + s.PW - pad > o.x &&
            s.py + pad < o.y + o.h && s.py + s.PH - pad > o.y) {
          s.dead = true;
          cancelAnimationFrame(rafRef.current);
          const finalScore = s.score;
          const finalCoins = s.coinsCollected;
          setScore(finalScore);
          setPhase('dead');
          submitScoreDB(finalScore, finalCoins).then(async (saved) => {
            if (saved) {
              const data = await fetchLeaderboard();
              if (data) {
                setBoard(data.leaderboard || []);
                setCached(data.leaderboard || []);
                if (data.my_best != null) {
                  const me = { score: data.my_best, rank: data.my_rank };
                  setMyBestDB(me);
                  try { localStorage.setItem(lsMyKey(), JSON.stringify(me)); } catch {}
                }
                if (data.my_coins != null) {
                  setMyCoins(data.my_coins);
                  try { localStorage.setItem(lsCoinsKey(), String(data.my_coins)); } catch {}
                }
              }
            } else {
              setMyCoins(prev => {
                const nc = prev + finalCoins;
                try { localStorage.setItem(lsCoinsKey(), String(nc)); } catch {}
                return nc;
              });
            }
          });
          return;
        }
      }

      // ── Draw ────────────────────────────────────────────────────────────────
      const { CW, CH, GROUND } = s;

      // Sky
      const sky = ctx.createLinearGradient(0, 0, 0, GROUND);
      sky.addColorStop(0, _C.skyTop);
      sky.addColorStop(1, _C.skyBot);
      ctx.fillStyle = sky;
      ctx.fillRect(0, 0, CW, CH);

      // Clouds
      ctx.fillStyle = _C.cloud;
      s.clouds.forEach(c => {
        ctx.beginPath(); ctx.ellipse(c.x, c.y, c.w * 0.5, c.h * 0.5, 0, 0, Math.PI * 2); ctx.fill();
        ctx.beginPath(); ctx.ellipse(c.x - c.w * 0.27, c.y + c.h * 0.15, c.w * 0.3, c.h * 0.44, 0, 0, Math.PI * 2); ctx.fill();
        ctx.beginPath(); ctx.ellipse(c.x + c.w * 0.24, c.y + c.h * 0.18, c.w * 0.27, c.h * 0.41, 0, 0, Math.PI * 2); ctx.fill();
      });

      // Ground
      const gGrad = ctx.createLinearGradient(0, GROUND, 0, CH);
      gGrad.addColorStop(0, _C.groundTop);
      gGrad.addColorStop(1, _C.groundBot);
      ctx.fillStyle = gGrad;
      ctx.fillRect(0, GROUND, CW, CH - GROUND);
      ctx.fillStyle = _C.groundLine;
      ctx.fillRect(0, GROUND, CW, 2);
      ctx.fillStyle = _C.groundDash;
      for (let x = -s.gOff; x < CW; x += 50) ctx.fillRect(x, GROUND + 6, 26, 2);

      // Coins
      s.coins.forEach(c => {
        if (c.collected) return;
        const pulse = 1 + Math.sin(s.frame * 0.12) * 0.07;
        ctx.save();
        ctx.shadowColor = '#f59e0b';
        ctx.shadowBlur = 12;
        ctx.fillStyle = '#f59e0b';
        ctx.beginPath(); ctx.arc(c.x, c.y, c.r * pulse, 0, Math.PI * 2); ctx.fill();
        ctx.shadowBlur = 0;
        ctx.fillStyle = '#fcd34d';
        ctx.beginPath(); ctx.arc(c.x - c.r * 0.22, c.y - c.r * 0.22, c.r * 0.33, 0, Math.PI * 2); ctx.fill();
        ctx.restore();
      });

      // Obstacles
      s.obstacles.forEach(o => drawObstacle(ctx, o, _isDark));

      // Player — sprite if loaded, else fallback
      const inAir   = s.py < s.GROUND - s.PH - 2;
      const animKey = inAir ? `${_skinBase}_jump` : `${_skinBase}_run`;
      const spr = spritesRef.current[animKey];
      if (spr) {
        const fi = Math.floor(s.frame / 4) % spr.frames;
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(spr.img, fi * spr.frameW, 0, spr.frameW, spr.frameH, s.PLAYER_X, s.py, s.PH, s.PH);
      } else {
        drawFallbackPlayer(ctx, s.PLAYER_X, s.py, s.PW, s.PH, s.frame, _skinColor, _isDark, GROUND);
      }

      // HUD — score (top right)
      const best = getCached()[0]?.score ?? 0;
      const hf = Math.max(9, CW * 0.014);
      ctx.textAlign = 'right';
      ctx.fillStyle = _C.hudMuted;
      ctx.font = `${hf}px monospace`;
      ctx.fillText(`HI ${String(best).padStart(5, '0')}`, CW - 10, hf + 6);
      ctx.fillStyle = _C.hudScore;
      ctx.font = `bold ${Math.max(13, CW * 0.021)}px monospace`;
      ctx.fillText(String(s.score).padStart(5, '0'), CW - 10, hf * 2 + 12);

      // HUD — coin icon + count (top left)
      const cr  = Math.max(5, CW * 0.009);
      const cx2 = 10 + cr, cy2 = 10 + cr;
      ctx.save();
      ctx.shadowColor = '#f59e0b'; ctx.shadowBlur = 6;
      ctx.fillStyle = '#f59e0b';
      ctx.beginPath(); ctx.arc(cx2, cy2, cr, 0, Math.PI * 2); ctx.fill();
      ctx.restore();
      ctx.fillStyle = _C.hudScore;
      ctx.font = `bold ${Math.max(10, CW * 0.016)}px monospace`;
      ctx.textAlign = 'left';
      ctx.fillText(s.coinsCollected, cx2 + cr + 4, cy2 + cr * 0.45);

      rafRef.current = requestAnimationFrame(loop);
    };

    rafRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(rafRef.current);
  }, [phase, isDark, skinObj.spriteBase]); // eslint-disable-line

  // ── Idle screen draw ───────────────────────────────────────────────────────
  useEffect(() => {
    if (phase !== 'idle') return;
    const canvas = canvasRef.current;
    if (!canvas || !canvas.width || !canvas.height) return;
    const ctx = canvas.getContext('2d');
    const CW = canvas.width, CH = canvas.height;
    const GROUND   = CH - Math.max(28, CH * 0.11);
    const PH       = Math.max(28, CW * 0.048);
    const PW       = Math.max(18, CW * 0.034);
    const PLAYER_X = Math.max(55, CW * 0.085);

    const sky = ctx.createLinearGradient(0, 0, 0, GROUND);
    sky.addColorStop(0, C.skyTop); sky.addColorStop(1, C.skyBot);
    ctx.fillStyle = sky; ctx.fillRect(0, 0, CW, CH);

    const gGrad = ctx.createLinearGradient(0, GROUND, 0, CH);
    gGrad.addColorStop(0, C.groundTop); gGrad.addColorStop(1, C.groundBot);
    ctx.fillStyle = gGrad; ctx.fillRect(0, GROUND, CW, CH - GROUND);
    ctx.fillStyle = C.groundLine; ctx.fillRect(0, GROUND, CW, 2);

    // Draw idle sprite or fallback
    const idleKey = `${skinObj.spriteBase}_idle`;
    const spr = spritesRef.current[idleKey];
    if (spr) {
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(spr.img, 0, 0, spr.frameW, spr.frameH, PLAYER_X, GROUND - PH, PH, PH);
    } else {
      drawFallbackPlayer(ctx, PLAYER_X, GROUND - PH, PW, PH, 0, skinColor, isDark, GROUND);
    }

    ctx.fillStyle = C.hudMuted;
    ctx.font = `${Math.max(12, CW * 0.02)}px monospace`;
    ctx.textAlign = 'center';
    ctx.fillText('tap or press space to start', CW / 2, GROUND * 0.45);
    ctx.textAlign = 'left';
  }, [phase, isDark, equippedSkin, cvsVersion, spritesReady]); // eslint-disable-line

  // ── Shop purchase ──────────────────────────────────────────────────────────
  const buySkin = useCallback(async (sk) => {
    const isOwned = ownedSkins.includes(sk.id) || sk.price === 0;
    if (isOwned) {
      setEquippedSkin(sk.id);
      try { localStorage.setItem(lsSkinKey(), sk.id); } catch {}
      setShopMsg(`Equipped ${sk.name}!`);
      setTimeout(() => setShopMsg(''), 1800);
      return;
    }
    if (myCoins < sk.price) {
      setShopMsg('Not enough coins!');
      setTimeout(() => setShopMsg(''), 1800);
      return;
    }
    const nc = myCoins - sk.price;
    const no = [...ownedSkins, sk.id];
    setMyCoins(nc); setOwnedSkins(no); setEquippedSkin(sk.id);
    try { localStorage.setItem(lsCoinsKey(), String(nc)); } catch {}
    try { localStorage.setItem(lsOwnedKey(), JSON.stringify(no)); } catch {}
    try { localStorage.setItem(lsSkinKey(), sk.id); } catch {}
    await spendCoinsDB(sk.price);
    setShopMsg(`Unlocked & equipped ${sk.name}!`);
    setTimeout(() => setShopMsg(''), 1800);
  }, [myCoins, ownedSkins]);

  const myBest    = myBestDB?.score ?? 0;
  const myRank    = myBestDB?.rank  ?? null;
  const highScore = board[0]?.score ?? 0;

  return (
    <div
      className="fixed inset-0 z-[9998] flex flex-col sm:items-center sm:justify-center sm:p-6"
      style={{ backgroundColor: isDark ? 'rgba(0,0,0,0.88)' : 'rgba(0,0,0,0.65)' }}
    >
      {/* Game card: full-screen on mobile, large centered card on desktop */}
      <div
        className="flex flex-col w-full h-full sm:h-[88vh] sm:max-w-5xl sm:rounded-2xl sm:overflow-hidden sm:shadow-2xl sm:border"
        style={{ backgroundColor: C.cardBg, borderColor: C.border }}
      >
        {/* ── Header ── */}
        <div className="flex-shrink-0 px-4 py-2.5 border-b" style={{ borderColor: C.border, backgroundColor: C.headerBg }}>
          <div className="flex items-center justify-between">
            <span className="font-bold text-sm" style={{ color: C.text }}>Campus Dash</span>
            <div className="flex items-center gap-1.5">
              {/* Coins balance */}
              <div
                className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-mono font-bold"
                style={{ backgroundColor: isDark ? '#21262d' : '#fef3c7', color: '#d97706' }}
              >
                <span style={{ fontSize: 11 }}>●</span> {myCoins}
              </div>
              {/* Shop */}
              <button
                onClick={() => setShowShop(true)}
                className="p-1.5 rounded-lg hover:opacity-70 transition-opacity"
                style={{ color: C.sub }} title="Character Shop"
              >
                <ShoppingBag size={15} />
              </button>
              {onClose && (
                <button onClick={onClose} className="p-1.5 rounded-lg hover:opacity-70 transition-opacity" style={{ color: C.sub }}>
                  <X size={15} />
                </button>
              )}
            </div>
          </div>

          {/* Stats row */}
          <div className="flex items-center gap-3 mt-1.5 flex-wrap text-xs">
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-lg"
              style={{ backgroundColor: isDark ? '#0d1117' : '#f0fdf4' }}>
              <Trophy size={10} color="#f59e0b" />
              <span style={{ color: C.sub }}>Best:</span>
              <span className="font-mono font-bold" style={{ color: C.hudScore }}>{myBest > 0 ? myBest : '—'}</span>
              {myRank != null && myRank > 0 && (
                <span className="px-1 py-px rounded text-[10px] font-semibold"
                  style={{
                    backgroundColor: myRank === 1 ? '#f59e0b22' : isDark ? '#3fb95022' : '#15803d22',
                    color: myRank === 1 ? '#f59e0b' : C.hudScore,
                  }}>#{myRank}</span>
              )}
            </div>
            {board.length > 0 && (
              <div className="flex items-center gap-1.5">
                <span style={{ color: C.sub }}>Top:</span>
                {board.slice(0, 5).map((e, i) => (
                  <span key={i} className="font-mono font-bold"
                    style={{ color: i === 0 ? '#f59e0b' : C.hudScore }}>{e.score}</span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ── Canvas ── */}
        <div
          ref={containerRef}
          className="relative cursor-pointer select-none flex-1 min-h-0"
          onClick={() => {
            if (showShop) return;
            if (phase === 'idle' || phase === 'dead') startGame();
            else doJump();
          }}
        >
          <canvas ref={canvasRef} className="block w-full h-full" style={{ touchAction: 'none' }} />

          {/* Game-over overlay */}
          {phase === 'dead' && !showShop && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2.5"
              style={{ backgroundColor: C.overlay }}>
              <p className="text-white font-bold text-2xl">Game Over</p>
              <p className="text-white/70 text-base">Score: <span className="font-bold text-white">{score}</span></p>
              {coinsThisRun > 0 && (
                <p className="text-sm font-semibold" style={{ color: '#f59e0b' }}>+{coinsThisRun} coins earned!</p>
              )}
              {score > 0 && score >= highScore && (
                <p className="text-sm font-bold px-3 py-1 rounded-full"
                  style={{ backgroundColor: '#f59e0b', color: '#0d1117' }}>New high score!</p>
              )}
              <button
                onClick={(e) => { e.stopPropagation(); startGame(); }}
                className="mt-1 flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold"
                style={{ backgroundColor: skinColor, color: '#fff' }}
              >
                <RotateCcw size={15} /> Play Again
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── Shop modal ── */}
      {showShop && (
        <div
          className="fixed inset-0 z-[9999] flex items-center justify-center p-4"
          style={{ backgroundColor: 'rgba(0,0,0,0.75)' }}
          onClick={() => setShowShop(false)}
        >
          <div
            className="w-full max-w-xs rounded-2xl p-4 shadow-2xl"
            style={{ backgroundColor: C.cardBg, border: `1px solid ${C.border}` }}
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="font-bold text-sm" style={{ color: C.text }}>Character Shop</span>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold" style={{ color: '#d97706' }}>● {myCoins}</span>
                <button onClick={() => setShowShop(false)} style={{ color: C.sub }}><X size={14} /></button>
              </div>
            </div>

            {shopMsg && (
              <div className="text-center text-xs font-semibold mb-2.5 py-1.5 rounded-lg"
                style={{ backgroundColor: isDark ? '#21262d' : '#f0fdf4', color: C.hudScore }}>
                {shopMsg}
              </div>
            )}

            <div className="grid grid-cols-2 gap-2.5">
              {SKINS.map(sk => {
                const owned    = ownedSkins.includes(sk.id) || sk.price === 0;
                const equipped = equippedSkin === sk.id;
                const canAfford = myCoins >= sk.price;
                const sc = isDark ? sk.color : sk.lightColor;
                return (
                  <div key={sk.id} className="rounded-xl p-3 border flex flex-col items-center gap-1.5"
                    style={{
                      borderColor: equipped ? sc : C.border,
                      backgroundColor: equipped ? `${sc}18` : (isDark ? '#0d1117' : '#f9fafb'),
                    }}>
                    {/* Sprite preview */}
                    <div className="w-13 h-13 flex items-center justify-center"
                      style={{ imageRendering: 'pixelated' }}>
                      <SkinPreview spriteBase={sk.spriteBase} frameCount={sk.idleFrames} size={52} />
                    </div>
                    <p className="text-xs font-semibold" style={{ color: C.text }}>{sk.name}</p>
                    <p className="text-[10px]" style={{ color: sk.price === 0 ? C.sub : '#d97706' }}>
                      {sk.price === 0 ? 'Free' : `● ${sk.price}`}
                    </p>
                    <button
                      onClick={() => buySkin(sk)}
                      disabled={!owned && !canAfford}
                      className="w-full text-[11px] font-semibold py-1 rounded-lg transition-all"
                      style={{
                        backgroundColor: equipped ? sc : (owned ? (isDark ? '#21262d' : '#e5e7eb') : (isDark ? '#161b22' : '#f3f4f6')),
                        color: equipped ? '#fff' : C.text,
                        opacity: (!owned && !canAfford) ? 0.4 : 1,
                        cursor: (!owned && !canAfford) ? 'not-allowed' : 'pointer',
                      }}
                    >
                      {equipped ? '✓ Equipped' : owned ? 'Equip' : 'Buy'}
                    </button>
                  </div>
                );
              })}
            </div>

            <p className="text-center text-[10px] mt-3" style={{ color: C.sub }}>
              Collect coins during runs to unlock characters
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
