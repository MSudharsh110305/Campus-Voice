import React, { useEffect, useState } from 'react';

export default function InstallPrompt() {
  const [deferredEvent, setDeferredEvent] = useState(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Capture the native beforeinstallprompt event
    const handler = (e) => {
      e.preventDefault();
      setDeferredEvent(e);
    };
    window.addEventListener('beforeinstallprompt', handler);

    // Feature 6: listen for custom trigger from Posts.jsx after first submission
    const customHandler = () => {
      if (deferredEvent) {
        setVisible(true);
      }
    };
    window.addEventListener('cv:show-install-prompt', customHandler);

    return () => {
      window.removeEventListener('beforeinstallprompt', handler);
      window.removeEventListener('cv:show-install-prompt', customHandler);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deferredEvent]);

  // Also show automatically when the browser fires beforeinstallprompt
  // (only if we haven't already stored the install-prompted flag)
  useEffect(() => {
    const autoHandler = (e) => {
      e.preventDefault();
      setDeferredEvent(e);
      // Auto-show only if not already prompted via the custom trigger flow
      if (!localStorage.getItem('cv_install_prompted')) {
        setVisible(true);
      }
    };
    window.addEventListener('beforeinstallprompt', autoHandler);
    return () => window.removeEventListener('beforeinstallprompt', autoHandler);
  }, []);

  if (!visible || !deferredEvent) return null;

  const onInstall = async () => {
    if (!deferredEvent) return;
    deferredEvent.prompt();
    await deferredEvent.userChoice;
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
          <button onClick={() => setVisible(false)} className="text-sm text-gray-600">Later</button>
          <button onClick={onInstall} className="text-sm bg-srec-primary hover:bg-srec-primaryHover text-white px-3 py-1.5 rounded-lg">Install</button>
        </div>
      </div>
    </div>
  );
}
