import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import AuthoritySidebar from '../components/AuthoritySidebar';
import AuthorityHeader from '../components/AuthorityHeader';
import { LogOut, Mail, Building, Shield, Smartphone } from 'lucide-react';

export default function AuthorityProfile({ noLayout = false }) {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [installPromptEvent, setInstallPromptEvent] = useState(null);
    const [isInstalled, setIsInstalled] = useState(false);
    const [showIosHint, setShowIosHint] = useState(false);

    useEffect(() => {
        const handler = (e) => { e.preventDefault(); setInstallPromptEvent(e); };
        window.addEventListener('beforeinstallprompt', handler);
        if (window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone) {
            setIsInstalled(true);
        }
        return () => window.removeEventListener('beforeinstallprompt', handler);
    }, []);

    const handleInstall = async () => {
        const isIos = /iphone|ipad|ipod/i.test(navigator.userAgent);
        if (installPromptEvent) {
            installPromptEvent.prompt();
            const { outcome } = await installPromptEvent.userChoice;
            if (outcome === 'accepted') setIsInstalled(true);
            setInstallPromptEvent(null);
        } else if (isIos) {
            setShowIosHint(v => !v);
        }
    };

    const initials = user?.name?.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || 'AU';

    const content = (
        <div className="p-6 max-w-lg mx-auto">
            {/* Avatar */}
            <div className="flex flex-col items-center mb-8">
                <div className="w-20 h-20 rounded-full bg-srec-primary/10 text-srec-primary flex items-center justify-center text-2xl font-bold mb-3">
                    {initials}
                </div>
                <h1 className="text-xl font-semibold text-gray-900">{user?.name || 'Authority User'}</h1>
                <p className="text-sm text-gray-400">{user?.authority_type || user?.designation || user?.role || 'Authority'}</p>
            </div>

            {/* Info rows */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm divide-y divide-gray-50">
                {[
                    { icon: Shield, label: 'Role', value: user?.authority_type || user?.role },
                    { icon: Building, label: 'Department', value: user?.department || 'All Departments' },
                    { icon: Mail, label: 'Email', value: user?.email },
                ].map(({ icon: Icon, label, value }) => (
                    <div key={label} className="flex items-center gap-4 px-5 py-4">
                        <Icon size={18} className="text-gray-400 flex-shrink-0" />
                        <div>
                            <p className="text-xs text-gray-400">{label}</p>
                            <p className="text-sm font-medium text-gray-900">{value || '—'}</p>
                        </div>
                    </div>
                ))}
            </div>

            {/* Install App */}
            {!isInstalled ? (
                <div className="mt-4">
                    <button
                        onClick={handleInstall}
                        className="w-full flex items-center justify-center gap-2 py-3 rounded-2xl border border-gray-200 text-gray-700 hover:bg-gray-50 active:bg-gray-100 transition-colors font-medium">
                        <Smartphone size={18} /> Install App
                    </button>
                    {showIosHint && (
                        <p className="text-xs text-gray-500 text-center mt-2 px-2">
                            Tap the <strong>Share</strong> button in Safari, then choose <strong>"Add to Home Screen"</strong>.
                        </p>
                    )}
                </div>
            ) : (
                <div className="w-full flex items-center justify-center gap-2 py-3 rounded-2xl border border-emerald-200 text-emerald-600 bg-emerald-50 text-sm font-medium mt-4">
                    <Smartphone size={18} /> App Installed
                </div>
            )}

            <button
                onClick={() => { logout(); navigate('/login'); }}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-2xl border border-red-200 text-red-600 hover:bg-red-50 active:bg-red-100 transition-colors font-medium mt-3">
                <LogOut size={18} /> Sign Out
            </button>
        </div>
    );

    // When used inside AdminLayout or AuthorityDashboard (noLayout=true),
    // skip rendering own sidebar/header — the parent layout already provides them.
    if (noLayout) {
        return <div className="animate-fadeIn">{content}</div>;
    }

    return (
        <div className="flex min-h-screen bg-srec-background">
            <AuthoritySidebar className="hidden md:flex fixed inset-y-0 left-0 z-10" />
            <div className="flex-1 md:ml-64 flex flex-col min-w-0 transition-all duration-300">
                <AuthorityHeader />
                <main className="flex-1 p-6 sm:p-8 overflow-y-auto animate-fadeIn">
                    {content}
                </main>
            </div>
        </div>
    );
}
