import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import adminService from '../../../services/admin.service';
import AdminComplaintCard from '../components/AdminComplaintCard';
import { DEPARTMENTS } from '../../../utils/constants';
import { Users, FileText, Building2, GraduationCap } from 'lucide-react';
import { Skeleton } from '../../../components/UI';

const TAB_STUDENTS = 'students';
const TAB_COMPLAINTS = 'complaints';

export default function AdminDepartmentDetail() {
    const { deptCode } = useParams();
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState(TAB_STUDENTS);
    const [students, setStudents] = useState([]);
    const [complaints, setComplaints] = useState([]);
    const [loadingStudents, setLoadingStudents] = useState(false);
    const [loadingComplaints, setLoadingComplaints] = useState(false);

    const dept = DEPARTMENTS.find(d => d.code === deptCode);

    useEffect(() => {
        loadStudents();
        loadComplaints();
    }, [deptCode]);

    const loadStudents = async () => {
        try {
            setLoadingStudents(true);
            const data = await adminService.getStudentsByDepartment(deptCode);
            const list = Array.isArray(data) ? data : data?.students || [];
            setStudents(list);
        } catch (err) {
            console.error('Failed to load students:', err);
            setStudents([]);
        } finally {
            setLoadingStudents(false);
        }
    };

    const loadComplaints = async () => {
        try {
            setLoadingComplaints(true);
            const data = await adminService.getDepartmentComplaints(deptCode);
            const list = Array.isArray(data) ? data : data?.complaints || [];
            setComplaints(list);
        } catch (err) {
            console.error('Failed to load complaints:', err);
            setComplaints([]);
        } finally {
            setLoadingComplaints(false);
        }
    };

    const token = localStorage.getItem('token');

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <button
                    onClick={() => navigate('/admin/departments/list')}
                    className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-srec-primary transition-colors mb-3"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                    </svg>
                    Back to Departments
                </button>

                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-srec-primary/10 flex items-center justify-center text-srec-primary flex-shrink-0">
                        <Building2 size={22} />
                    </div>
                    <div>
                        <div className="flex items-center gap-2 mb-0.5">
                            <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-srec-primary/10 text-srec-primary">
                                {deptCode}
                            </span>
                        </div>
                        <h1 className="text-2xl font-bold text-gray-900">
                            {dept?.name || deptCode}
                        </h1>
                    </div>
                </div>

                {/* Summary stats */}
                <div className="grid grid-cols-2 gap-4 mt-5">
                    <div className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm flex items-center gap-3">
                        <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center text-blue-600">
                            <Users size={18} />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-gray-900">{loadingStudents ? '—' : students.length}</p>
                            <p className="text-xs text-gray-500 font-medium">Students</p>
                        </div>
                    </div>
                    <div className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm flex items-center gap-3">
                        <div className="w-10 h-10 bg-amber-50 rounded-xl flex items-center justify-center text-amber-600">
                            <FileText size={18} />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-gray-900">{loadingComplaints ? '—' : complaints.length}</p>
                            <p className="text-xs text-gray-500 font-medium">Complaints</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 bg-gray-100 rounded-xl p-1 w-fit">
                <button
                    onClick={() => setActiveTab(TAB_STUDENTS)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200 ${
                        activeTab === TAB_STUDENTS
                            ? 'bg-white text-srec-primary shadow-sm'
                            : 'text-gray-500 hover:text-gray-700'
                    }`}
                >
                    <Users size={15} />
                    Students
                    {!loadingStudents && students.length > 0 && (
                        <span className="ml-1 px-1.5 py-0.5 bg-srec-primary/10 text-srec-primary rounded-full text-[10px] font-bold">
                            {students.length}
                        </span>
                    )}
                </button>
                <button
                    onClick={() => setActiveTab(TAB_COMPLAINTS)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200 ${
                        activeTab === TAB_COMPLAINTS
                            ? 'bg-white text-srec-primary shadow-sm'
                            : 'text-gray-500 hover:text-gray-700'
                    }`}
                >
                    <FileText size={15} />
                    Complaints
                    {!loadingComplaints && complaints.length > 0 && (
                        <span className="ml-1 px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded-full text-[10px] font-bold">
                            {complaints.length}
                        </span>
                    )}
                </button>
            </div>

            {/* Students Tab */}
            {activeTab === TAB_STUDENTS && (
                <div>
                    {loadingStudents ? (
                        <div className="space-y-3">
                            {[1, 2, 3].map(i => <Skeleton key={i} className="h-16 rounded-xl" />)}
                        </div>
                    ) : students.length === 0 ? (
                        <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center shadow-sm">
                            <div className="w-14 h-14 mx-auto mb-3 bg-gray-50 rounded-full flex items-center justify-center">
                                <GraduationCap size={26} className="text-gray-400" />
                            </div>
                            <p className="text-gray-700 font-semibold">No students found</p>
                            <p className="text-gray-400 text-sm mt-1">No students registered under this department yet.</p>
                        </div>
                    ) : (
                        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="bg-gray-50 border-b border-gray-100">
                                        <th className="text-left px-5 py-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Roll No</th>
                                        <th className="text-left px-5 py-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Name</th>
                                        <th className="text-left px-5 py-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Year</th>
                                        <th className="text-left px-5 py-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Email</th>
                                        <th className="text-left px-5 py-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Stay Type</th>
                                        <th className="text-left px-5 py-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Status</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-50">
                                    {students.map((student, idx) => (
                                        <tr key={student.roll_no || idx} className="hover:bg-gray-50/50 transition-colors">
                                            <td className="px-5 py-3.5 font-mono font-semibold text-srec-primary text-xs">
                                                {student.roll_no}
                                            </td>
                                            <td className="px-5 py-3.5 font-medium text-gray-900">
                                                {student.name || '—'}
                                            </td>
                                            <td className="px-5 py-3.5 text-gray-500">
                                                {student.year ? `Year ${student.year}` : '—'}
                                            </td>
                                            <td className="px-5 py-3.5 text-gray-500 text-xs">
                                                {student.email || '—'}
                                            </td>
                                            <td className="px-5 py-3.5">
                                                <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                                                    student.stay_type === 'Hostel'
                                                        ? 'bg-blue-50 text-blue-700'
                                                        : 'bg-gray-100 text-gray-600'
                                                }`}>
                                                    {student.stay_type || '—'}
                                                </span>
                                            </td>
                                            <td className="px-5 py-3.5">
                                                <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                                                    student.is_active !== false
                                                        ? 'bg-green-50 text-green-700'
                                                        : 'bg-red-50 text-red-600'
                                                }`}>
                                                    {student.is_active !== false ? 'Active' : 'Inactive'}
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}

            {/* Complaints Tab */}
            {activeTab === TAB_COMPLAINTS && (
                <div>
                    {loadingComplaints ? (
                        <div className="space-y-4">
                            {[1, 2, 3].map(i => <Skeleton key={i} className="h-32 rounded-xl" />)}
                        </div>
                    ) : complaints.length === 0 ? (
                        <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center shadow-sm">
                            <div className="w-14 h-14 mx-auto mb-3 bg-gray-50 rounded-full flex items-center justify-center">
                                <FileText size={26} className="text-gray-400" />
                            </div>
                            <p className="text-gray-700 font-semibold">No complaints found</p>
                            <p className="text-gray-400 text-sm mt-1">No department complaints registered for {deptCode} yet.</p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {complaints.map(complaint => (
                                <AdminComplaintCard
                                    key={complaint.id}
                                    complaint={complaint}
                                    token={token}
                                />
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
