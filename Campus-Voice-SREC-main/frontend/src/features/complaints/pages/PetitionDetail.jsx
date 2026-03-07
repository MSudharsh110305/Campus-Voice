import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import petitionService from '../../../services/petition.service';
import { TopNav } from '../../../components/Navbars';
import BottomNav from '../../../components/BottomNav';
import { useAuth } from '../../../context/AuthContext';
import {
  ArrowLeft, Clock, CheckCircle, AlertTriangle,
  Globe, Building2, Home, Lock, ShieldCheck,
} from 'lucide-react';

const STATUS_BADGE = {
  Open: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  Acknowledged: 'bg-amber-50 text-amber-700 border-amber-200',
  Resolved: 'bg-blue-50 text-blue-700 border-blue-200',
  Closed: 'bg-gray-100 text-gray-500 border-gray-200',
};

const SCOPE_ICONS = { General: Globe, Department: Building2, Hostel: Home };
const SCOPE_COLORS = {
  General: 'bg-sky-50 text-sky-700 border-sky-200',
  Department: 'bg-purple-50 text-purple-700 border-purple-200',
  Hostel: 'bg-orange-50 text-orange-700 border-orange-200',
};

const MILESTONES = [50, 100, 250];

function checkAccess(petition, user) {
  if (!petition || !user) return { allowed: false, reason: 'Please log in to view this petition.' };

  // Creator always has access to their own petition regardless of scope
  if (petition.created_by_roll_no && petition.created_by_roll_no === user.roll_no) {
    return { allowed: true };
  }

  const scope = petition.petition_scope;

  if (scope === 'Hostel') {
    if (user.stay_type !== 'Hostel') {
      return { allowed: false, reason: 'This petition is only visible to hostel residents.' };
    }
  }

  if (scope === 'Department') {
    const sameDept =
      user.department_id && petition.department_id &&
      String(user.department_id) === String(petition.department_id);
    if (!sameDept) {
      return { allowed: false, reason: `This petition is only visible to students in the ${petition.department_name || 'same'} department.` };
    }
  }

  if (!petition.is_published && user.role?.toLowerCase() === 'student') {
    return { allowed: false, reason: 'This petition is pending approval and not yet published.' };
  }

  return { allowed: true };
}

export default function PetitionDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [petition, setPetition] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [signing, setSigning] = useState(false);
  const [signMsg, setSignMsg] = useState('');

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    petitionService.getPetitionDetail(id)
      .then(data => setPetition(data))
      .catch(err => setError(err.message || 'Failed to load petition'))
      .finally(() => setLoading(false));
  }, [id]);

  const handleSign = async () => {
    setSigning(true);
    setSignMsg('');
    try {
      const res = await petitionService.signPetition(id);
      setSignMsg(res.message || (petition.signed_by_me ? 'Signature removed.' : 'Signed!'));
      setPetition(prev => ({
        ...prev,
        signed_by_me: !prev.signed_by_me,
        signature_count: prev.signed_by_me ? prev.signature_count - 1 : prev.signature_count + 1,
      }));
    } catch (err) {
      setSignMsg(err.message || 'Failed to sign petition');
    } finally {
      setSigning(false);
      setTimeout(() => setSignMsg(''), 3000);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-srec-background">
        <TopNav />
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-4 border-srec-primary border-t-transparent rounded-full animate-spin" />
        </div>
        {user?.role === 'Student' && <BottomNav />}
      </div>
    );
  }

  if (error || !petition) {
    return (
      <div className="min-h-screen bg-srec-background">
        <TopNav />
        <div className="max-w-xl mx-auto p-6 pb-24 md:pl-24">
          <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-gray-500 hover:text-gray-800 mb-6 text-sm">
            <ArrowLeft size={16} /> Back
          </button>
          <div className="bg-white rounded-2xl border border-gray-100 p-8 text-center shadow-sm">
            <AlertTriangle size={40} className="mx-auto text-red-400 mb-3" />
            <p className="text-gray-700 font-medium">{error || 'Petition not found.'}</p>
            <button onClick={() => navigate('/petitions')} className="mt-4 text-sm text-srec-primary underline">
              View all petitions
            </button>
          </div>
        </div>
        {user?.role === 'Student' && <BottomNav />}
      </div>
    );
  }

  const access = checkAccess(petition, user);

  if (!access.allowed) {
    return (
      <div className="min-h-screen bg-srec-background">
        <TopNav />
        <div className="max-w-xl mx-auto p-6 pb-24 md:pl-24">
          <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-gray-500 hover:text-gray-800 mb-6 text-sm">
            <ArrowLeft size={16} /> Back
          </button>
          <div className="bg-white rounded-2xl border border-gray-100 p-8 text-center shadow-sm">
            <Lock size={40} className="mx-auto text-gray-300 mb-3" />
            <h2 className="text-lg font-bold text-gray-900 mb-2">Access Restricted</h2>
            <p className="text-gray-500 text-sm">{access.reason}</p>
            <button onClick={() => navigate('/petitions')} className="mt-6 text-sm text-srec-primary underline">
              View petitions available to you
            </button>
          </div>
        </div>
        {user?.role === 'Student' && <BottomNav />}
      </div>
    );
  }

  const {
    title, description, petition_scope, status, signature_count,
    custom_goal, milestone_goal, milestones_reached = [], progress_pct,
    days_remaining, deadline, is_extended, authority_response,
    department_name, created_by_name, created_at,
  } = petition;

  const goal = custom_goal || milestone_goal || 50;
  const isSigned = petition.signed_by_me;
  const isOwner = petition.created_by_roll_no === user?.roll_no;
  const isClosed = status === 'Resolved' || status === 'Closed';
  const isExpired = days_remaining !== null && days_remaining !== undefined && days_remaining <= 0;
  const goalReached = signature_count >= goal;

  const ScopeIcon = SCOPE_ICONS[petition_scope] || Globe;

  const formattedDate = created_at
    ? new Date(created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
    : null;

  return (
    <div className="min-h-screen bg-srec-background">
      <TopNav />
      <div className="max-w-2xl mx-auto p-4 sm:p-6 pb-24 md:pl-24 animate-fadeIn">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-gray-500 hover:text-gray-800 mb-5 text-sm transition-colors"
        >
          <ArrowLeft size={16} /> Back to Petitions
        </button>

        <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-white/60 shadow-[0_4px_24px_-4px_rgba(0,0,0,0.08)] overflow-hidden">
          {/* Status accent bar */}
          <div className={`h-1 w-full ${
            status === 'Open' ? 'bg-emerald-500' :
            status === 'Acknowledged' ? 'bg-amber-400' :
            status === 'Resolved' ? 'bg-blue-500' : 'bg-gray-300'
          }`} />

          <div className="p-5 sm:p-6">
            {/* Badges */}
            <div className="flex flex-wrap gap-1.5 mb-3">
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${STATUS_BADGE[status] || STATUS_BADGE.Open}`}>
                {status}
              </span>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border inline-flex items-center gap-1 ${SCOPE_COLORS[petition_scope] || SCOPE_COLORS.General}`}>
                <ScopeIcon size={9} /> {petition_scope || 'General'}
              </span>
              {department_name && (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-50 text-purple-600 border border-purple-200">
                  {department_name}
                </span>
              )}
              {is_extended && (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-green-50 text-green-700 border border-green-200">
                  +4d Extended
                </span>
              )}
              {goalReached && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <CheckCircle size={9} /> Goal Reached!
                </span>
              )}
              {isExpired && !isClosed && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-50 text-red-600 border border-red-200">
                  <AlertTriangle size={9} /> Expired
                </span>
              )}
            </div>

            {/* Title */}
            <h1 className="text-xl sm:text-2xl font-bold text-gray-900 leading-snug mb-3">{title}</h1>

            {/* Meta */}
            <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500 mb-5">
              {created_by_name && <span>By <strong className="text-gray-700">{created_by_name}</strong></span>}
              {formattedDate && <span>{formattedDate}</span>}
              {deadline && !isExpired && days_remaining !== null && (
                <span className={`inline-flex items-center gap-1 font-medium ${days_remaining <= 3 ? 'text-orange-600' : 'text-gray-500'}`}>
                  <Clock size={11} /> {days_remaining}d left
                </span>
              )}
            </div>

            {/* Description */}
            <div className="mb-6 p-4 bg-gray-50 rounded-xl border border-gray-100 text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
              {description}
            </div>

            {/* Progress */}
            <div className="mb-6">
              <div className="flex justify-between items-end mb-2">
                <div>
                  <span className="text-2xl font-bold text-gray-900">{signature_count}</span>
                  <span className="text-sm text-gray-400 ml-1">/ {goal} signatures</span>
                </div>
                <span className="text-sm font-bold text-srec-primary">{Math.min(progress_pct || 0, 100)}%</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
                <div
                  className={`h-3 rounded-full transition-all duration-700 ${
                    goalReached
                      ? 'bg-gradient-to-r from-emerald-500 to-emerald-400'
                      : 'bg-gradient-to-r from-srec-primary to-emerald-500'
                  }`}
                  style={{ width: `${Math.min(progress_pct || 0, 100)}%` }}
                />
              </div>
              {/* Milestones */}
              <div className="flex gap-1.5 mt-2 flex-wrap">
                {MILESTONES.filter(m => m <= goal * 3).map((m) => (
                  <span
                    key={m}
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold border transition-all ${
                      milestones_reached.includes(m)
                        ? 'bg-amber-100 text-amber-700 border-amber-300'
                        : 'bg-gray-50 text-gray-400 border-gray-200'
                    }`}
                  >
                    {milestones_reached.includes(m) ? '🏆' : '○'} {m}
                  </span>
                ))}
              </div>
            </div>

            {/* Authority response */}
            {authority_response && (
              <div className="mb-6 p-4 bg-blue-50 rounded-xl border border-blue-100">
                <div className="flex items-center gap-2 mb-1">
                  <ShieldCheck size={14} className="text-blue-600" />
                  <p className="text-[10px] font-bold uppercase tracking-wider text-blue-600">Official Response</p>
                </div>
                <p className="text-sm text-blue-800">{authority_response}</p>
              </div>
            )}

            {/* Sign feedback */}
            {signMsg && (
              <div className={`mb-4 p-3 rounded-xl text-sm text-center font-medium ${
                signMsg.toLowerCase().includes('fail') || signMsg.toLowerCase().includes('error')
                  ? 'bg-red-50 text-red-600 border border-red-100'
                  : 'bg-emerald-50 text-emerald-700 border border-emerald-100'
              }`}>
                {signMsg}
              </div>
            )}

            {/* Sign button */}
            {!isClosed && !isOwner && !isExpired && (
              <button
                onClick={handleSign}
                disabled={signing}
                className={`w-full py-3 rounded-xl text-sm font-bold border transition-all duration-200 ${
                  isSigned
                    ? 'bg-srec-primarySoft text-srec-primary border-srec-primaryMuted/40 hover:bg-red-50 hover:text-red-600 hover:border-red-200'
                    : 'bg-srec-primary text-white border-srec-primary hover:bg-srec-primaryDark shadow-btn active:scale-[0.97]'
                } disabled:opacity-60`}
              >
                {signing ? 'Processing...' : isSigned ? '✓ Signed — Click to Unsign' : '✍ Sign this Petition'}
              </button>
            )}

            {isClosed && (
              <div className="w-full py-3 rounded-xl text-sm font-bold border bg-gray-50 text-gray-400 border-gray-200 text-center">
                This petition is {status.toLowerCase()}
              </div>
            )}

            {isOwner && !isClosed && (
              <div className="w-full py-3 rounded-xl text-sm font-medium border bg-srec-primarySoft text-srec-primary border-srec-primaryMuted/30 text-center">
                You created this petition
              </div>
            )}
          </div>
        </div>
      </div>
      {user?.role === 'Student' && <BottomNav />}
    </div>
  );
}
