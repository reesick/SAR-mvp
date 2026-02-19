import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
    BarChart3,
    Search,
    LogOut,
    AlertTriangle,
    CheckCircle,
    Clock,
    Menu,
    X,
    FileText,
    Settings
} from 'lucide-react';
import { api } from '../services/api';

function Dashboard() {
    const { logout } = useAuth();
    const navigate = useNavigate();

    const [customerId, setCustomerId] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [sidebarOpen, setSidebarOpen] = useState(true);

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    const runAnalysis = async (e) => {
        e.preventDefault();
        if (!customerId) return;

        setLoading(true);
        setError('');

        try {
            const caseRes = await api.createCase(parseInt(customerId));
            const caseId = caseRes.data.case_id;
            const analysisRes = await api.runAnalysis(caseId, parseInt(customerId));
            navigate(`/cases/${caseId}`, {
                state: {
                    sarDraft: analysisRes.data.sar_draft,
                    riskScore: analysisRes.data.risk_score,
                    recommendation: analysisRes.data.recommended_action,
                    qualityScore: analysisRes.data.quality_score,
                    matchedTypologies: analysisRes.data.matched_typologies || []
                }
            });
        } catch (err) {
            setError(err.response?.data?.detail || 'Analysis failed. Check Backend Logs.');
            setLoading(false);
        }
    };

    return (
        <div className="flex h-screen bg-slate-50 overflow-hidden">
            {/* Sidebar */}
            <motion.aside
                initial={{ x: -100 }}
                animate={{ x: 0 }}
                className={`${sidebarOpen ? 'w-64' : 'w-20'} bg-slate-900 text-white transition-all duration-300 flex flex-col z-20`}
            >
                <div className="h-20 flex items-center justify-between px-6 border-b border-slate-800">
                    {sidebarOpen && <span className="text-xl font-bold bg-gradient-to-r from-sky-400 to-emerald-400 text-transparent bg-clip-text">AML Mind</span>}
                    <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-1 hover:bg-slate-800 rounded">
                        {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
                    </button>
                </div>

                <nav className="flex-1 py-6 space-y-2 px-3">
                    <NavItem icon={<BarChart3 />} label="Dashboard" active={true} expanded={sidebarOpen} onClick={() => { }} />
                    <NavItem icon={<FileText />} label="Customers" expanded={sidebarOpen} onClick={() => navigate('/customers')} />
                    <NavItem icon={<Settings />} label="Settings" expanded={sidebarOpen} onClick={() => { }} />
                </nav>

                <div className="p-4 border-t border-slate-800">
                    <button
                        onClick={handleLogout}
                        className={`flex items-center ${sidebarOpen ? 'justify-start px-4' : 'justify-center'} py-3 w-full text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl transition-colors`}
                    >
                        <LogOut size={20} />
                        {sidebarOpen && <span className="ml-3 font-medium">Sign Out</span>}
                    </button>
                </div>
            </motion.aside>

            {/* Main Content */}
            <main className="flex-1 overflow-y-auto">
                <header className="h-20 bg-white border-b border-slate-100 flex items-center justify-between px-8 sticky top-0 z-10">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-800">Dashboard</h1>
                        <p className="text-sm text-slate-500">Welcome back, Officer</p>
                    </div>
                    <div className="flex items-center space-x-4">
                        <div className="w-10 h-10 bg-sky-100 rounded-full flex items-center justify-center text-sky-600 font-bold border-2 border-white shadow-sm">
                            A
                        </div>
                    </div>
                </header>

                <div className="p-8 max-w-7xl mx-auto space-y-8">

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <StatCard icon={<AlertTriangle className="text-amber-500" />} label="High Risk Cases" value="12" change="+2 today" color="amber" />
                        <StatCard icon={<CheckCircle className="text-emerald-500" />} label="Cases Closed" value="84" change="+5 this week" color="emerald" />
                        <StatCard icon={<Clock className="text-sky-500" />} label="Avg Analysis Time" value="45s" change="-12% vs last week" color="sky" />
                    </div>

                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="bg-white rounded-2xl shadow-sm border border-slate-100 p-8"
                    >
                        <div className="max-w-xl mx-auto text-center">
                            <div className="w-16 h-16 bg-gradient-to-br from-indigo-500 to-sky-500 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg shadow-sky-200">
                                <Search className="text-white w-8 h-8" />
                            </div>
                            <h2 className="text-2xl font-bold text-slate-800 mb-2">Start New Investigation</h2>
                            <p className="text-slate-500 mb-8">Enter a Customer ID to trigger the autonomous AI pipeline.</p>

                            <form onSubmit={runAnalysis} className="relative max-w-md mx-auto">
                                <input
                                    type="text"
                                    placeholder="Enter Customer ID (e.g. 11)"
                                    value={customerId}
                                    onChange={(e) => setCustomerId(e.target.value)}
                                    className="w-full pl-6 pr-32 py-4 bg-slate-50 border border-slate-200 rounded-2xl focus:ring-2 focus:ring-sky-500 focus:border-transparent outline-none transition-all text-lg font-medium shadow-inner"
                                />
                                <button
                                    type="submit"
                                    disabled={loading}
                                    className="absolute right-2 top-2 bottom-2 bg-slate-900 hover:bg-slate-800 text-white px-6 rounded-xl font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                                >
                                    {loading ? <span className="animate-pulse">Running...</span> : <span>Analyze</span>}
                                </button>
                            </form>

                            {error && (
                                <div className="mt-4 p-3 bg-red-50 text-red-600 rounded-lg text-sm border border-red-100 inline-block">
                                    {error}
                                </div>
                            )}
                        </div>
                    </motion.div>

                    <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
                        <div className="bg-slate-50/50 px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                            <h3 className="font-semibold text-slate-700">Recent Investigations</h3>
                            <button className="text-sm text-sky-600 font-medium hover:text-sky-700">View All</button>
                        </div>
                        <table className="w-full">
                            <thead className="bg-slate-50/50 text-left">
                                <tr>
                                    <th className="px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Case ID</th>
                                    <th className="px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Target</th>
                                    <th className="px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                                    <th className="px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Date</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {[1, 2, 3].map((_, i) => (
                                    <tr key={i} className="hover:bg-slate-50/50 transition-colors">
                                        <td className="px-6 py-4 text-sm font-medium text-slate-900">#CASE-2026-{800 + i}</td>
                                        <td className="px-6 py-4 text-sm text-slate-600">Customer {7 + i}</td>
                                        <td className="px-6 py-4">
                                            <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${i === 0 ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}`}>
                                                {i === 0 ? 'High Risk' : 'Cleared'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-sm text-slate-500">Feb {18 - i}, 2026</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </main>
        </div>
    );
}

const NavItem = ({ icon, label, active, expanded, onClick }) => (
    <button onClick={onClick} className={`flex items-center w-full p-3 rounded-xl transition-colors ${active ? 'bg-sky-500/10 text-sky-400' : 'text-slate-400 hover:text-white hover:bg-slate-800'} ${!expanded && 'justify-center'}`}>
        {React.cloneElement(icon, { size: 20 })}
        {expanded && <span className="ml-3 font-medium">{label}</span>}
    </button>
);

const StatCard = ({ icon, label, value, change }) => (
    <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
        <div className="flex items-start justify-between mb-4">
            <div className="p-3 bg-slate-50 rounded-xl">
                {icon}
            </div>
            {change && <span className="text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-1 rounded-lg">{change}</span>}
        </div>
        <h3 className="text-3xl font-bold text-slate-800 mb-1">{value}</h3>
        <p className="text-sm text-slate-500 font-medium">{label}</p>
    </div>
);

export default Dashboard;
