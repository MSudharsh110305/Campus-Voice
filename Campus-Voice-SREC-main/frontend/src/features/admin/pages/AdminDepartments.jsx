import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import adminService from '../../../services/admin.service';
import { Building2, Home, FileText, ChevronRight, ShieldAlert, Briefcase } from 'lucide-react';

// Complaint categories handled by the system
const COMPLAINT_CATEGORIES = [
    {
        id: 'mens-hostel',
        label: "Men's Hostel",
        icon: Home,
        color: 'blue',
        description: 'Complaints from male hostel residents',
        filterKey: "Men's Hostel",
    },
    {
        id: 'womens-hostel',
        label: "Women's Hostel",
        icon: Home,
        color: 'pink',
        description: 'Complaints from female hostel residents',
        filterKey: "Women's Hostel",
    },
    {
        id: 'general',
        label: 'General',
        icon: Briefcase,
        color: 'green',
        description: 'Campus-wide general complaints',
        filterKey: 'General',
    },
    {
        id: 'department',
        label: 'Department',
        icon: Building2,
        color: 'amber',
        description: 'Academic department-specific complaints',
        filterKey: 'Department',
    },
    {
        id: 'disciplinary',
        label: 'Disciplinary Committee',
        icon: ShieldAlert,
        color: 'red',
        description: 'Disciplinary and conduct-related issues',
        filterKey: 'Disciplinary Committee',
    },
];

const COLOR_MAP = {
    blue:  { icon: 'bg-blue-100 text-blue-600',   border: 'border-blue-100',  hover: 'hover:border-blue-300' },
    pink:  { icon: 'bg-pink-100 text-pink-600',   border: 'border-pink-100',  hover: 'hover:border-pink-300' },
    green: { icon: 'bg-green-100 text-green-600', border: 'border-green-100', hover: 'hover:border-green-300' },
    amber: { icon: 'bg-amber-100 text-amber-600', border: 'border-amber-100', hover: 'hover:border-amber-300' },
    red:   { icon: 'bg-red-100 text-red-600',     border: 'border-red-100',   hover: 'hover:border-red-300'  },
};

function CategoryCard({ cat, total, onClick }) {
    const Icon = cat.icon;
    const c = COLOR_MAP[cat.color] || COLOR_MAP.green;

    return (
        <div
            onClick={onClick}
            className={`bg-white rounded-2xl p-6 border ${c.border} ${c.hover} hover:shadow-lg hover:scale-[1.02] transition-all duration-200 cursor-pointer group`}
        >
            <div className="flex items-start justify-between mb-4">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${c.icon}`}>
                    <Icon size={22} />
                </div>
                <ChevronRight size={18} className="text-gray-300 group-hover:text-gray-500 group-hover:translate-x-1 transition-all duration-200 mt-1" />
            </div>

            <h3 className="text-lg font-bold text-gray-900 mb-1">{cat.label}</h3>
            <p className="text-xs text-gray-500 mb-4 leading-relaxed">{cat.description}</p>

            <div className="flex items-center justify-between pt-4 border-t border-gray-100">
                <span className="flex items-center gap-1.5 text-sm text-gray-500">
                    <FileText size={14} />
                    Complaints
                </span>
                <span className="text-lg font-bold text-gray-900">{total ?? '—'}</span>
            </div>
        </div>
    );
}

export default function AdminDepartments() {
    const navigate = useNavigate();
    const [overview, setOverview] = useState(null);

    useEffect(() => {
        adminService.getSystemOverview().then(setOverview).catch(console.error);
    }, []);

    const byCategory = overview?.complaints_by_category || {};

    // Try to match category name (partial match for flexibility)
    const getTotal = (filterKey) => {
        let total = 0;
        Object.entries(byCategory).forEach(([key, val]) => {
            if (key === filterKey || key.toLowerCase().includes(filterKey.toLowerCase())) {
                total += val;
            }
        });
        return total;
    };

    const handleCategoryClick = (cat) => {
        if (cat.id === 'department') {
            navigate('/admin/departments/list');
        } else {
            navigate(`/admin/complaints?category=${encodeURIComponent(cat.filterKey)}`);
        }
    };

    return (
        <div className="space-y-8">
            <div>
                <h1 className="text-2xl font-bold text-gray-900">Complaint Categories</h1>
                <p className="text-gray-500 mt-1">Browse complaints by category. Click any card to view filtered complaints.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {COMPLAINT_CATEGORIES.map(cat => (
                    <CategoryCard
                        key={cat.id}
                        cat={cat}
                        total={getTotal(cat.filterKey)}
                        onClick={() => handleCategoryClick(cat)}
                    />
                ))}
            </div>

            {/* Quick link to all complaints */}
            <div
                onClick={() => navigate('/admin/complaints')}
                className="bg-gradient-to-r from-srec-primary to-srec-primaryHover rounded-2xl p-6 text-white cursor-pointer hover:shadow-xl transition-all duration-200 flex items-center justify-between group"
            >
                <div>
                    <h3 className="text-lg font-bold mb-1">View All Complaints</h3>
                    <p className="text-white/70 text-sm">See every complaint across all categories with full filter controls</p>
                </div>
                <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center group-hover:bg-white/30 transition-colors">
                    <ChevronRight size={20} className="group-hover:translate-x-0.5 transition-transform" />
                </div>
            </div>
        </div>
    );
}
