import React from 'react';
import { Card } from '../UI.jsx';

const StatsCard = ({ label, value, icon: Icon, color = 'green', className = '', onClick }) => {
    const colorStyles = {
        green: 'bg-srec-primary/10 text-srec-primary',
        blue: 'bg-blue-50 text-blue-700',
        yellow: 'bg-srec-gold/10 text-yellow-700', // Gold background with dark text for readability
        red: 'bg-srec-danger/10 text-srec-danger',
        gray: 'bg-gray-50 text-gray-700',
        purple: 'bg-purple-50 text-purple-700',
    };

    return (
        <div
            onClick={onClick}
            className={`bg-white rounded-2xl p-5 border border-gray-100 shadow-[6px_6px_16px_rgba(0,0,0,0.06),-6px_-6px_16px_rgba(255,255,255,0.9)] flex items-center gap-4 transition-all hover:shadow-lg ${onClick ? 'cursor-pointer hover:shadow-md hover:border-gray-200' : ''} ${className}`}
        >
            {Icon && (
                <div className={`p-3 rounded-xl ${colorStyles[color] || colorStyles.green}`}>
                    <Icon size={24} />
                </div>
            )}
            <div>
                <h4 className="text-2xl font-bold text-gray-900 leading-tight">{value}</h4>
                <p className="text-sm text-gray-500 font-medium mt-1">{label}</p>
            </div>
        </div>
    );
};

export default StatsCard;
