import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
    BarChart3,
    Search,
    LogOut,
    Menu,
    X,
    FileText,
    Settings,
    Zap
} from 'lucide-react';
import { api } from '../services/api';

const QUICK_CUSTOMERS = [
    { id: 1, name: 'Customer 1' },
    { id: 2, name: 'Customer 2' },
    { id: 3, name: 'Customer 3' },
    { id: 4, name: 'Customer 4' },
    { id: 5, name: 'Customer 5' },
    { id: 6, name: 'Customer 6' },
    { id: 7, name: 'Customer 7' },
    { id: 8, name: 'Customer 8' },
    { id: 9, name: 'Customer 9' },
    { id: 10, name: 'Customer 10' },
    { id: 11, name: 'Customer 11' },
    { id: 12, name: 'Customer 12' },
];

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
                    <NavItem icon={<Settings />} label="Settings" expanded={sidebarOpen} onClick={() => alert('Settings coming soon!')} />
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

                    {/* Quick Customer Picker */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6"
                    >
                        <div className="flex items-center gap-2 mb-4">
                            <div className="p-2 bg-indigo-50 rounded-lg">
                                <Zap className="text-indigo-500 w-4 h-4" />
                            </div>
                            <h3 className="font-semibold text-slate-700">Quick Select Customer</h3>
                            <span className="text-xs text-slate-400 ml-1">— click to auto-fill ID below</span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {QUICK_CUSTOMERS.map((c) => (
                                <button
                                    key={c.id}
                                    onClick={() => setCustomerId(String(c.id))}
                                    className={`px-4 py-2 rounded-xl text-sm font-medium border transition-all duration-150
                                        ${customerId === String(c.id)
                                            ? 'bg-slate-900 text-white border-slate-900 shadow-md'
                                            : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-sky-50 hover:border-sky-300 hover:text-sky-700'
                                        }`}
                                >
                                    #{c.id}
                                </button>
                            ))}
                        </div>
                    </motion.div>

                    {/* Investigation Form */}
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
                            <p className="text-slate-500 mb-8">Enter a Customer ID to trigger the autonomous AI pipeline.(wait for 5-10 seconds)</p>

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

                    {/* Recent Investigations */}
                    <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
                        <div className="bg-slate-50/50 px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                            <h3 className="font-semibold text-slate-700">Recent Investigations</h3>
                            <button onClick={() => navigate('/customers')} className="text-sm text-sky-600 font-medium hover:text-sky-700">View All</button>
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
                                <tr>
                                    <td colSpan={4} className="px-6 py-10 text-center text-slate-400 text-sm">
                                        No investigations yet. Select a customer above to get started.
                                    </td>
                                </tr>
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

export default Dashboard;