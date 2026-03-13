import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Eye, EyeOff, GraduationCap, ShieldCheck } from "lucide-react";
import { useAuth } from "../../../context/AuthContext";

export default function LoginPage() {
  const { loginStudent, loginAuthority, user, loading } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [mode, setMode] = useState(searchParams.get("role") === "authority" ? "authority" : "student");
  const [identifier, setIdentifier] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  React.useEffect(() => {
    if (!loading && user) {
      if (user.role === "Admin") navigate("/admin", { replace: true });
      else if (user.role === "Authority") navigate("/authority-dashboard", { replace: true });
      else navigate("/home", { replace: true });
    }
  }, [user, loading, navigate]);

  const switchMode = (newMode) => { setMode(newMode); setError(""); setPassword(""); };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (mode === "student") {
      if (!identifier || !password) { setError("Please fill in both email/roll number and password."); return; }
      try {
        setIsLoading(true);
        await loginStudent(identifier, password);
        navigate("/dashboard", { replace: true });
      } catch (err) {
        setError(err.message || "Login failed. Check your credentials.");
      } finally { setIsLoading(false); }
    } else {
      if (!email || !password) { setError("Please fill in both email and password."); return; }
      try {
        setIsLoading(true);
        const response = await loginAuthority(email, password);
        if (response.role === "Admin") navigate("/admin", { replace: true });
        else navigate("/authority-dashboard", { replace: true });
      } catch (err) {
        setError(err.message || "Login failed. Check your credentials.");
      } finally { setIsLoading(false); }
    }
  };

  const inputClass = "w-full rounded-xl border border-gray-200 bg-gray-50/50 px-4 py-3 text-sm text-gray-900 placeholder:text-gray-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary transition-all font-medium";

  return (
    <div className="min-h-screen bg-srec-background flex items-center justify-center px-4">
      <div className="w-full max-w-[420px]">

        {/* Brand header */}
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-srec-primaryLight to-srec-primary flex items-center justify-center text-white font-bold text-xl shadow-lg shadow-srec-primary/20 mx-auto mb-4">
            CV
          </div>
          <h1 className="text-2xl font-bold text-srec-primary tracking-tight">CampusVoice</h1>
          <p className="text-gray-400 text-sm mt-1">SREC Grievance Redressal Portal</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          {/* Pill tab switcher */}
          <div className="flex bg-gray-50 border-b border-gray-100 p-3 gap-2">
            <button
              type="button"
              onClick={() => switchMode("student")}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-semibold rounded-full transition-all duration-200 ${
                mode === "student"
                  ? "bg-white shadow-sm text-srec-primary"
                  : "text-gray-400 hover:text-gray-600"
              }`}
            >
              <GraduationCap size={15} /> Student
            </button>
            <button
              type="button"
              onClick={() => switchMode("authority")}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-semibold rounded-full transition-all duration-200 ${
                mode === "authority"
                  ? "bg-white shadow-sm text-srec-primary"
                  : "text-gray-400 hover:text-gray-600"
              }`}
            >
              <ShieldCheck size={15} /> Faculty / Staff
            </button>
          </div>

          <form onSubmit={onSubmit} className="p-6 space-y-4">
            {mode === "student" ? (
              <div>
                <input
                  type="text"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  className={inputClass}
                  placeholder="Roll number or email (e.g. 22CS123)"
                />
              </div>
            ) : (
              <div>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={inputClass}
                  placeholder="authority@srec.ac.in"
                />
              </div>
            )}

            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={`${inputClass} pr-11`}
                placeholder="Password"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700" role="alert">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 bg-srec-primary text-white font-semibold rounded-xl hover:bg-srec-primaryHover transition-all duration-200 shadow-sm disabled:opacity-60 disabled:cursor-not-allowed text-sm mt-1"
            >
              {isLoading ? "Signing In..." : mode === "student" ? "Sign In as Student" : "Access Authority Portal"}
            </button>
          </form>
        </div>

        {mode === "student" && (
          <div className="mt-5 text-center">
            <span className="text-gray-500 text-sm">Don't have an account? </span>
            <Link to="/signup" className="text-srec-primary font-semibold hover:underline transition-colors">Create Account</Link>
          </div>
        )}
        {mode === "authority" && (
          <p className="mt-5 text-center text-xs text-gray-400">Authority accounts are managed by the system administrator.</p>
        )}
      </div>
    </div>
  );
}
