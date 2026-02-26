import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import adminService from '../../../services/admin.service';
import { DEPARTMENTS } from '../../../utils/constants';
import { Building2, FileText, ChevronRight, Users } from 'lucide-react';
import { Skeleton } from '../../../components/UI';

function DepartmentCard({ dept, complaintCount, studentCount, onClick }) {
    return (
        <div
            onClick={onClick}
            className="bg-white rounded-2xl border border-gray-100 hover:border-emerald-200 hover:shadow-lg hover:shadow-emerald-50 hover:scale-[1.02] transition-all duration-200 cursor-pointer group overflow-hidden"
        >
            {/* Top accent strip */}
            <div className="h-1 w-full bg-gradient-to-r from-srec-primary via-emerald-600 to-green-500" />

            <div className="p-5">
                <div className="flex items-start justify-between mb-3">
                    <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-srec-primary/10 to-emerald-50 flex items-center justify-center text-srec-primary border border-emerald-100">
                        <Building2 size={20} />
                    </div>
                    <ChevronRight size={16} className="text-gray-300 group-hover:text-srec-primary group-hover:translate-x-1 transition-all duration-200 mt-1" />
                </div>

                <div className="mb-1">
                    <span className="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200 mb-2">
                        {dept.code}
                    </span>
                </div>
                <h3 className="text-sm font-bold text-gray-900 leading-snug">{dept.name}</h3>

                <div className="flex items-center gap-3 pt-3.5 border-t border-gray-50 mt-3.5">
                    <div className="flex items-center gap-1.5 bg-amber-50 border border-amber-100 rounded-lg px-2.5 py-1">
                        <FileText size={12} className="text-amber-600" />
                        <span className="font-bold text-amber-700 text-sm">{complaintCount ?? '—'}</span>
                        <span className="text-[10px] text-amber-600">issues</span>
                    </div>
                    <div className="flex items-center gap-1.5 bg-blue-50 border border-blue-100 rounded-lg px-2.5 py-1">
                        <Users size={12} className="text-blue-600" />
                        <span className="font-bold text-blue-700 text-sm">{studentCount ?? '—'}</span>
                        <span className="text-[10px] text-blue-600">students</span>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function AdminDepartmentsList() {
    const navigate = useNavigate();
    const [overview, setOverview] = useState(null);
    const [studentCounts, setStudentCounts] = useState({});
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const loadData = async () => {
            try {
                setLoading(true);
                const data = await adminService.getSystemOverview().catch(() => null);
                setOverview(data);
                // Use students_by_department from overview if available
                if (data?.students_by_department) {
                    setStudentCounts(data.students_by_department);
                }
            } catch (err) {
                console.error('Failed to load department data:', err);
            } finally {
                setLoading(false);
            }
        };
        loadData();
    }, []);

    // Get complaint count by dept code from overview
    const getComplaintCount = (deptCode) => {
        if (!overview) return null;
        const byDept = overview.complaints_by_department || {};
        return byDept[deptCode] ?? null;
    };

    if (loading) {
        return (
            <div className="space-y-6">
                <div>
                    <div className="h-8 w-48 bg-gray-200 rounded-lg animate-pulse mb-2" />
                    <div className="h-4 w-96 bg-gray-100 rounded animate-pulse" />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {[1, 2, 3, 4, 5, 6].map(i => (
                        <Skeleton key={i} className="h-44 rounded-2xl" />
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <button
                        onClick={() => navigate('/admin/departments')}
                        className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-srec-primary transition-colors mb-2"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                        </svg>
                        Back to Categories
                    </button>
                    <h1 className="text-2xl font-bold text-gray-900">Engineering Departments</h1>
                    <p className="text-gray-500 mt-1">
                        Browse all {DEPARTMENTS.length} departments. Click a department to see its students and complaints.
                    </p>
                </div>
            </div>

            {/* Department Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {DEPARTMENTS.map(dept => (
                    <DepartmentCard
                        key={dept.code}
                        dept={dept}
                        complaintCount={getComplaintCount(dept.code)}
                        studentCount={studentCounts[dept.code] ?? null}
                        onClick={() => navigate(`/admin/departments/${dept.code}`)}
                    />
                ))}
            </div>

            {/* Quick link to all department complaints */}
            <div
                onClick={() => navigate('/admin/complaints?category=Department')}
                className="bg-gradient-to-r from-srec-primary to-srec-primaryHover rounded-2xl p-6 text-white cursor-pointer hover:shadow-xl transition-all duration-200 flex items-center justify-between group"
            >
                <div>
                    <h3 className="text-lg font-bold mb-1">View All Department Complaints</h3>
                    <p className="text-white/70 text-sm">See every department complaint with full filter controls</p>
                </div>
                <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center group-hover:bg-white/30 transition-colors">
                    <ChevronRight size={20} className="group-hover:translate-x-0.5 transition-transform" />
                </div>
            </div>
        </div>
    );
}
