import React, { useState, useEffect } from 'react';
import { WifiOff, Loader2, CheckCircle } from 'lucide-react';
import { getPendingComplaints, deletePendingComplaint } from '../utils/idb';
import { tokenStorage } from '../utils/api';

export default function OfflineIndicator() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [syncing, setSyncing] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);
  const [justSynced, setJustSynced] = useState(false);

  useEffect(() => {
    const handleOnline = async () => {
      setIsOnline(true);
      const pending = await getPendingComplaints().catch(() => []);
      if (pending.length > 0) {
        setPendingCount(pending.length);
        await submitPending(pending);
      }
    };
    const handleOffline = () => {
      setIsOnline(false);
      setJustSynced(false);
    };
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    // Check pending on mount
    getPendingComplaints().then(p => setPendingCount(p.length)).catch(() => {});
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

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
      } catch (e) { /* network still down, retry later */ }
    }
    setSyncing(false);
    if (submitted > 0) {
      setJustSynced(true);
      setPendingCount(0);
      setTimeout(() => setJustSynced(false), 3000);
    }
  };

  if (isOnline && !syncing && !justSynced) return null;

  const bgClass = isOnline
    ? justSynced ? 'bg-emerald-500' : 'bg-blue-500'
    : 'bg-gray-900';

  return (
    <div className={`fixed top-0 left-0 right-0 z-[9999] flex items-center justify-center gap-2 py-2 px-4 text-xs font-medium text-white transition-all ${bgClass}`}>
      {!isOnline && <><WifiOff size={13} /> Offline — draft saved, will submit when connected</>}
      {isOnline && syncing && <><Loader2 size={13} className="animate-spin" /> Submitting {pendingCount} queued complaint{pendingCount !== 1 ? 's' : ''}…</>}
      {isOnline && justSynced && <><CheckCircle size={13} /> Queued complaints submitted successfully!</>}
    </div>
  );
}
