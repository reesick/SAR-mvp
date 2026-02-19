import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import {
    ArrowLeft,
    Users,
    AlertTriangle,
    Shield,
    Search,
    Play
} from 'lucide-react';
import { motion } from 'framer-motion';

function Customers() {
    const navigate = useNavigate();
    const [customers, setCustomers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [runningId, setRunningId] = useState(null);

    useEffect(() => {
        loadCustomers();
    }, []);

    const loadCustomers = async () => {
        try {
            const res = await api.getCustomers();
            setCustomers(res.data);
        } catch (err) {
            console.error('Failed to load customers:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleAnalyze = async (customerId) => {
        setRunningId(customerId);
        try {
            const caseRes = await api.createCase(customerId);
            const caseId = caseRes.data.case_id;
            const analysisRes = await api.runAnalysis(caseId, customerId);
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
            alert(err.response?.data?.detail || 'Analysis failed');
            setRunningId(null);
        }
    };

    const filtered = customers.filter(c =>
        c.name.toLowerCase().includes(search.toLowerCase()) ||
        c.id.toString().includes(search) ||
        c.risk_profile.toLowerCase().includes(search.toLowerCase())
    );

    const riskColor = (profile) => {
        if (profile === 'HIGH') return { bg: '#fef2f2', text: '#dc2626', border: '#fecaca' };
        if (profile === 'MEDIUM') return { bg: '#fffbeb', text: '#b45309', border: '#fde68a' };
        return { bg: '#f0f9ff', text: '#0369a1', border: '#bae6fd' };
    };

    return (
        <div className="min-h-screen bg-sky-50" style={{ fontFamily: "'Poppins', sans-serif" }}>
            {/* Header */}
            <header className="bg-white border-b border-sky-100 h-16 sticky top-0 z-30 flex items-center justify-between px-6 shadow-sm">
                <div className="flex items-center space-x-4">
                    <button
                        onClick={() => navigate('/dashboard')}
                        className="p-2 hover:bg-sky-50 rounded-full text-slate-500 transition-colors"
                    >
                        <ArrowLeft size={20} />
                    </button>
                    <h1 className="text-lg font-bold text-slate-800 flex items-center">
                        <Users size={20} className="mr-2 text-sky-600" />
                        Customer Database
                    </h1>
                </div>
                <div className="relative w-72">
                    <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input
                        type="text"
                        placeholder="Search by name, ID, or risk..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="w-full pl-9 pr-4 py-2 bg-sky-50 border border-sky-200 rounded-lg focus:ring-2 focus:ring-sky-400 focus:border-transparent outline-none text-sm"
                    />
                </div>
            </header>

            {/* Content */}
            <div className="p-6 max-w-6xl mx-auto">
                {loading ? (
                    <div className="text-center py-20 text-slate-400">
                        <div className="animate-spin w-8 h-8 border-2 border-sky-400 border-t-transparent rounded-full mx-auto mb-3"></div>
                        Loading customers...
                    </div>
                ) : (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="bg-white rounded-xl shadow-sm border border-sky-100 overflow-hidden"
                    >
                        <table className="w-full">
                            <thead>
                                <tr className="bg-sky-50 border-b border-sky-100">
                                    <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">ID</th>
                                    <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Customer Name</th>
                                    <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Risk</th>
                                    <th className="px-5 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Accounts</th>
                                    <th className="px-5 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Transactions</th>
                                    <th className="px-5 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Balance</th>
                                    <th className="px-5 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-sky-50">
                                {filtered.map((c) => {
                                    const rc = riskColor(c.risk_profile);
                                    const isRunning = runningId === c.id;
                                    return (
                                        <tr key={c.id} className="hover:bg-sky-50/50 transition-colors">
                                            <td className="px-5 py-4 text-sm font-mono text-slate-600">{c.id}</td>
                                            <td className="px-5 py-4 text-sm font-semibold text-slate-800">{c.name}</td>
                                            <td className="px-5 py-4">
                                                <span
                                                    className="px-2.5 py-1 rounded-full text-xs font-bold flex items-center w-fit"
                                                    style={{ backgroundColor: rc.bg, color: rc.text, border: `1px solid ${rc.border}` }}
                                                >
                                                    {c.risk_profile === 'HIGH' && <AlertTriangle size={12} className="mr-1" />}
                                                    {c.risk_profile === 'LOW' && <Shield size={12} className="mr-1" />}
                                                    {c.risk_profile}
                                                </span>
                                            </td>
                                            <td className="px-5 py-4 text-sm text-slate-600 text-right">{c.account_count}</td>
                                            <td className="px-5 py-4 text-sm text-slate-600 text-right">{c.transaction_count}</td>
                                            <td className="px-5 py-4 text-sm font-medium text-slate-700 text-right">
                                                ${c.total_balance?.toLocaleString()}
                                            </td>
                                            <td className="px-5 py-4 text-center">
                                                <button
                                                    onClick={() => handleAnalyze(c.id)}
                                                    disabled={isRunning}
                                                    className="inline-flex items-center px-3 py-1.5 text-xs font-semibold text-white bg-sky-600 rounded-lg hover:bg-sky-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                                >
                                                    {isRunning ? (
                                                        <span className="animate-pulse">Running...</span>
                                                    ) : (
                                                        <>
                                                            <Play size={12} className="mr-1" />
                                                            Analyze
                                                        </>
                                                    )}
                                                </button>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>

                        {filtered.length === 0 && (
                            <div className="text-center py-12 text-slate-400 text-sm">
                                No customers match your search.
                            </div>
                        )}
                    </motion.div>
                )}

                <p className="text-center text-xs text-slate-400 mt-4">
                    Showing {filtered.length} of {customers.length} customers
                </p>
            </div>
        </div>
    );
}

export default Customers;
