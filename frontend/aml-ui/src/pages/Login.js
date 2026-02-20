import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { User, Lock, ArrowRight, Loader, Copy, Check } from 'lucide-react';
import { api } from '../services/api';

const DEMO_EMAIL = 'shreevirajmatale25@gmail.com';
const DEMO_PASS = 's@12';

function CopyButton({ text }) {
    const [copied, setCopied] = useState(false);
    const handleCopy = () => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };
    return (
        <button
            type="button"
            onClick={handleCopy}
            className="ml-2 p-1 rounded-md hover:bg-slate-200 transition-colors text-slate-500 hover:text-sky-600"
            title="Copy"
        >
            {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
        </button>
    );
}

function Login() {
    const [isRegister, setIsRegister] = useState(false);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const { login } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            if (isRegister) {
                await api.register(email, password);
                setIsRegister(false);
                setError('');
                alert('Registration successful! Please sign in.');
            } else {
                const response = await api.login(email, password);
                login(response.data.access_token);
                navigate('/dashboard');
            }
        } catch (err) {
            setError(err.response?.data?.detail || 'Authentication failed. Check credentials.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-indigo-500 via-sky-500 to-emerald-500 flex items-center justify-center p-4">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="w-full max-w-md bg-white/90 backdrop-blur-xl rounded-2xl shadow-2xl overflow-hidden"
            >
                <div className="p-8">
                    <div className="text-center mb-8">
                        <h1 className="text-3xl font-bold text-slate-800 tracking-tight">
                            {isRegister ? 'Create Account' : 'Welcome Back'}
                        </h1>
                        <p className="text-slate-500 mt-2">
                            {isRegister ? 'Join the AML Investigation Team' : 'Sign into your dashboard'}
                        </p>
                    </div>

                    {/* Demo Credentials Box */}
{!isRegister && (
    <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6 p-4 bg-sky-50 border border-sky-200 rounded-xl text-sm"
    >
        <p className="text-sky-700 font-semibold mb-2 text-xs uppercase tracking-wide">
            🔑 Demo Credentials
        </p>

        {/* Backend Activation Notice */}
        <div className="mb-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-amber-700 text-xs leading-relaxed">
                ⚠️ Before signing in, please activate the backend by clicking{" "}
                <a
                    href="https://sar-mvp.onrender.com/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline font-medium"
                >
                    https://sar-mvp.onrender.com/
                </a>{" "}
                or wait 1–2 minutes for the backend to restart.
            </p>
        </div>

        <div className="space-y-1.5">
            <div className="flex items-center justify-between bg-white rounded-lg px-3 py-1.5 border border-sky-100">
                <span className="text-slate-500 text-xs mr-2 shrink-0">Email:</span>
                <span className="text-slate-800 font-medium text-xs truncate">
                    {DEMO_EMAIL}
                </span>
                <CopyButton text={DEMO_EMAIL} />
            </div>

            <div className="flex items-center justify-between bg-white rounded-lg px-3 py-1.5 border border-sky-100">
                <span className="text-slate-500 text-xs mr-2 shrink-0">Password:</span>
                <span className="text-slate-800 font-medium text-xs">
                    {DEMO_PASS}
                </span>
                <CopyButton text={DEMO_PASS} />
            </div>
        </div>
    </motion.div>
)}

                    {error && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="bg-red-50 text-red-500 p-3 rounded-lg mb-6 text-sm flex items-center justify-center font-medium border border-red-100"
                        >
                            {error}
                        </motion.div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-slate-700 ml-1">Email Address</label>
                            <div className="relative">
                                <User className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 h-5 w-5" />
                                <input
                                    type="email"
                                    required
                                    className="w-full pl-10 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-sky-500 focus:border-transparent outline-none transition-all text-slate-800 placeholder:text-slate-400 font-medium"
                                    placeholder="name@agency.gov"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium text-slate-700 ml-1">Password</label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 h-5 w-5" />
                                <input
                                    type="password"
                                    required
                                    className="w-full pl-10 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-sky-500 focus:border-transparent outline-none transition-all text-slate-800 placeholder:text-slate-400 font-medium"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full bg-slate-900 hover:bg-slate-800 text-white font-semibold py-3.5 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center group"
                        >
                            {loading ? (
                                <Loader className="animate-spin h-5 w-5" />
                            ) : (
                                <>
                                    {isRegister ? 'Get Started' : 'Sign In'}
                                    <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
                                </>
                            )}
                        </button>
                    </form>

                    <div className="mt-8 text-center">
                        <button
                            type="button"
                            onClick={() => setIsRegister(!isRegister)}
                            className="text-slate-500 hover:text-sky-600 font-medium text-sm transition-colors"
                        >
                            {isRegister ? 'Already have an account? Sign in' : "Don't have an account? Sign up"}
                        </button>
                    </div>
                </div>

                <div className="h-1.5 bg-gradient-to-r from-indigo-500 via-sky-500 to-emerald-500" />
            </motion.div>
        </div>
    );
}

export default Login;