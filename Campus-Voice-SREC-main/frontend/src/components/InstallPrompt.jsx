import React, { useEffect, useState } from 'react';

export default function InstallPrompt() {
  const [deferredEvent, setDeferredEvent] = useState(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Single handler: update state whenever the prompt is (re-)captured
    const capture = (e) => {
      e.preventDefault();
      window._deferredInstallPrompt = e;
      setDeferredEvent(e);
      if (!localStorage.getItem('cv_install_prompted')) {
        setVisible(true);
      }
    };

    // Pick up prompt already captured in index.jsx (fires before component mounts)
    if (window._deferredInstallPrompt && !localStorage.getItem('cv_install_prompted')) {
      setDeferredEvent(window._deferredInstallPrompt);
      setVisible(true);
    }

    window.addEventListener('beforeinstallprompt', capture);

    // Custom trigger dispatched from Posts.jsx after first complaint submission
    const customTrigger = () => {
      const prompt = window._deferredInstallPrompt;
      if (prompt) {
        setDeferredEvent(prompt);
        setVisible(true);
      }
    };
    window.addEventListener('cv:show-install-prompt', customTrigger);

    return () => {
      window.removeEventListener('beforeinstallprompt', capture);
      window.removeEventListener('cv:show-install-prompt', customTrigger);
    };
  }, []); // single effect, run once on mount

  if (!visible || !deferredEvent) return null;

  const dismiss = () => {
    setVisible(false);
    localStorage.setItem('cv_install_prompted', '1');
  };

  const onInstall = async () => {
    if (!deferredEvent) return;
    deferredEvent.prompt();
    const { outcome } = await deferredEvent.userChoice;
    if (outcome === 'accepted') {
      window._deferredInstallPrompt = null;
      localStorage.setItem('cv_install_prompted', '1');
    }
    setVisible(false);
    setDeferredEvent(null);
  };

  return (
    <div className="fixed bottom-4 inset-x-0 px-4 z-50">
      <div className="mx-auto max-w-md bg-white border border-gray-200 shadow-lg rounded-xl p-3 flex items-center justify-between">
        <div>
          <div className="text-sm font-medium text-gray-900">Install Campus Voice</div>
          <div className="text-xs text-gray-600">Add to your home screen for quick access.</div>
        </div>
        <div className="flex gap-2">
          <button onClick={dismiss} className="text-sm text-gray-600 px-2 py-1">Later</button>
          <button onClick={onInstall} className="text-sm bg-srec-primary hover:bg-srec-primaryHover text-white px-3 py-1.5 rounded-lg">Install</button>
        </div>
      </div>
    </div>
  );
}
