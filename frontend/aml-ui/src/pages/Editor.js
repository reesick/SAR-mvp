import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import {
    ArrowLeft,
    Download,
    FileText,
    AlertTriangle,
    ShieldCheck,
    Activity,
    Target,
    CheckCircle,
    XCircle
} from 'lucide-react';
import { motion } from 'framer-motion';

function Editor() {
    const { caseId } = useParams();
    const location = useLocation();
    const navigate = useNavigate();
    const { sarDraft, riskScore, recommendation, qualityScore, matchedTypologies } = location.state || {};

    const [content, setContent] = useState(sarDraft || '');
    const [auditData, setAuditData] = useState(null);
    const [isExporting, setIsExporting] = useState(false);
    const [activeTab, setActiveTab] = useState('typology');

    const loadAuditData = useCallback(async () => {
        try {
            const response = await api.getCase(caseId);
            setAuditData(response.data);
        } catch (err) {
            console.error('Failed to load audit data:', err);
        }
    }, [caseId]);

    useEffect(() => {
        loadAuditData();
    }, [loadAuditData]);

    const handleExport = async (format) => {
        setIsExporting(true);
        try {
            const exportData = {
                sar_text: content,
                risk_score: riskScore || 0,
                recommendation: recommendation || "UNKNOWN"
            };

            const response = format === 'docx'
                ? await api.exportDocx(caseId, exportData)
                : await api.exportPdf(caseId, exportData);

            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `SAR_${caseId}.${format}`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) {
            console.error(err);
            alert('Export failed');
        } finally {
            setIsExporting(false);
        }
    };

    const isHighRisk = riskScore > 0.3;
    const primaryTypology = matchedTypologies?.[0];
    const qualityColor = qualityScore >= 80 ? 'sky' : qualityScore >= 50 ? 'amber' : 'red';

    return (
        <div className="min-h-screen bg-sky-50 flex flex-col" style={{ fontFamily: "'Poppins', sans-serif" }}>
            {/* Header */}
            <header className="bg-white border-b border-sky-100 h-16 sticky top-0 z-30 flex items-center justify-between px-6 shadow-sm">
                <div className="flex items-center space-x-4">
                    <button
                        onClick={() => navigate('/dashboard')}
                        className="p-2 hover:bg-sky-50 rounded-full text-slate-500 transition-colors"
                    >
                        <ArrowLeft size={20} />
                    </button>
                    <div className="flex flex-col">
                        <h1 className="text-lg font-bold text-slate-800 flex items-center">
                            SAR Editor
                            <span className="ml-3 text-xs font-normal text-slate-400 bg-sky-50 px-2 py-0.5 rounded-md border border-sky-100">#{caseId?.substring(0, 8)}</span>
                        </h1>
                    </div>
                </div>

                <div className="flex items-center space-x-3">
                    {/* Risk Badge */}
                    <div className={`flex items-center px-3 py-1.5 rounded-full text-sm font-semibold ${isHighRisk ? 'bg-amber-50 text-amber-700 border border-amber-200' : 'bg-sky-50 text-sky-700 border border-sky-200'}`}>
                        {isHighRisk ? <AlertTriangle size={16} className="mr-2" /> : <ShieldCheck size={16} className="mr-2" />}
                        Risk: {riskScore != null ? (riskScore * 100).toFixed(0) + '%' : 'N/A'}
                    </div>

                    {/* Quality Badge */}
                    {qualityScore != null && (
                        <div className={`flex items-center px-3 py-1.5 rounded-full text-sm font-semibold bg-${qualityColor}-50 text-${qualityColor}-700 border border-${qualityColor}-200`}
                            style={{
                                backgroundColor: qualityScore >= 80 ? '#f0f9ff' : qualityScore >= 50 ? '#fffbeb' : '#fef2f2',
                                color: qualityScore >= 80 ? '#0369a1' : qualityScore >= 50 ? '#b45309' : '#dc2626',
                                borderColor: qualityScore >= 80 ? '#bae6fd' : qualityScore >= 50 ? '#fde68a' : '#fecaca'
                            }}
                        >
                            {qualityScore >= 80 ? <CheckCircle size={16} className="mr-2" /> : <XCircle size={16} className="mr-2" />}
                            Quality: {qualityScore}/100
                        </div>
                    )}

                    <div className="h-6 w-px bg-sky-100 mx-2" />

                    <button
                        onClick={() => handleExport('docx')}
                        disabled={isExporting}
                        className="flex items-center px-4 py-2 text-slate-700 bg-white border border-sky-200 rounded-lg hover:bg-sky-50 font-medium text-sm transition-colors"
                    >
                        <FileText size={16} className="mr-2 text-sky-600" />
                        Word
                    </button>
                    <button
                        onClick={() => handleExport('pdf')}
                        disabled={isExporting}
                        className="flex items-center px-4 py-2 text-white bg-sky-600 rounded-lg hover:bg-sky-700 font-medium text-sm transition-colors shadow-sm"
                    >
                        <Download size={16} className="mr-2" />
                        PDF
                    </button>
                </div>
            </header>

            {/* Main Layout */}
            <div className="flex-1 flex overflow-hidden">
                {/* Editor Column */}
                <div className="flex-1 overflow-y-auto p-8 relative">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="max-w-3xl mx-auto bg-white shadow-lg rounded-xl min-h-[700px] p-12 border border-sky-100"
                    >
                        <div className="border-b-2 border-sky-600 pb-6 mb-8 flex justify-between items-start">
                            <div>
                                <h2 className="text-2xl font-bold uppercase tracking-widest text-slate-800">Suspicious Activity Report</h2>
                                <p className="text-sm text-slate-400 mt-1">CONFIDENTIAL • FINA GEN-2026</p>
                            </div>
                            <div className="text-right">
                                <p className="text-xs font-bold text-slate-400">CASE REFERENCE</p>
                                <p className="text-lg font-mono text-slate-700">{caseId?.substring(0, 8)}</p>
                            </div>
                        </div>

                        {/* Recommendation Banner */}
                        <div className={`mb-6 p-4 rounded-lg border-l-4 ${isHighRisk ? 'bg-amber-50 border-amber-400 text-amber-900' : 'bg-sky-50 border-sky-400 text-sky-900'}`}>
                            <h3 className="font-bold text-sm uppercase tracking-wide opacity-70 mb-1">AI Recommendation</h3>
                            <p className="font-semibold text-lg">{recommendation || 'Pending analysis...'}</p>
                        </div>

                        {/* Typology Match Card */}
                        {primaryTypology && (
                            <div className="mb-6 p-4 rounded-lg bg-sky-50 border border-sky-200">
                                <div className="flex items-center justify-between mb-2">
                                    <h3 className="font-bold text-sm uppercase tracking-wide text-sky-700 flex items-center">
                                        <Target size={16} className="mr-2" />
                                        Matched Typology
                                    </h3>
                                    <span className="text-sm font-bold text-sky-700 bg-white px-3 py-1 rounded-full border border-sky-200">
                                        {(primaryTypology.confidence * 100).toFixed(0)}% match
                                    </span>
                                </div>
                                <p className="font-semibold text-slate-800 text-lg mb-2">{primaryTypology.name}</p>
                                <p className="text-xs text-slate-500 mb-3">{primaryTypology.regulatory_reference}</p>

                                {primaryTypology.evidence?.length > 0 && (
                                    <div className="space-y-1">
                                        {primaryTypology.evidence.slice(0, 5).map((e, i) => (
                                            <div key={i} className="flex items-start text-sm text-slate-600">
                                                <span className="text-sky-500 mr-2 mt-0.5">•</span>
                                                <span>{e}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        <textarea
                            value={content}
                            onChange={(e) => setContent(e.target.value)}
                            className="w-full h-[500px] resize-none outline-none text-slate-700 leading-relaxed text-base placeholder:text-slate-300"
                            style={{ fontFamily: "'Poppins', sans-serif" }}
                            placeholder="Start writing the SAR narrative here..."
                        />

                        <div className="mt-12 pt-6 border-t border-sky-100 text-center text-xs text-slate-400">
                            Generated by Agentic AML System • Authorized Personnel Only
                        </div>
                    </motion.div>
                </div>

                {/* Right Sidebar — Tabbed */}
                <div className="w-96 bg-white border-l border-sky-100 overflow-y-auto hidden xl:flex xl:flex-col">
                    {/* Tabs */}
                    <div className="flex border-b border-sky-100 bg-sky-50/50 sticky top-0 z-10">
                        <button
                            onClick={() => setActiveTab('typology')}
                            className={`flex-1 py-3 text-sm font-semibold transition-colors ${activeTab === 'typology' ? 'text-sky-700 border-b-2 border-sky-500 bg-white' : 'text-slate-400 hover:text-slate-600'}`}
                        >
                            <Target size={14} className="inline mr-1.5 -mt-0.5" />
                            Typology
                        </button>
                        <button
                            onClick={() => setActiveTab('audit')}
                            className={`flex-1 py-3 text-sm font-semibold transition-colors ${activeTab === 'audit' ? 'text-sky-700 border-b-2 border-sky-500 bg-white' : 'text-slate-400 hover:text-slate-600'}`}
                        >
                            <Activity size={14} className="inline mr-1.5 -mt-0.5" />
                            Audit Trail
                        </button>
                    </div>

                    <div className="flex-1 overflow-y-auto">
                        {/* Typology Tab */}
                        {activeTab === 'typology' && (
                            <div className="p-5 space-y-5">
                                {/* Summary Stats */}
                                <div className="grid grid-cols-2 gap-3">
                                    <div className="bg-sky-50 rounded-lg p-3 border border-sky-100 text-center">
                                        <p className="text-2xl font-bold text-sky-700">{riskScore != null ? (riskScore * 100).toFixed(0) + '%' : '—'}</p>
                                        <p className="text-xs text-slate-500 font-medium">Risk Score</p>
                                    </div>
                                    <div className="rounded-lg p-3 border text-center"
                                        style={{
                                            backgroundColor: qualityScore >= 80 ? '#f0f9ff' : qualityScore >= 50 ? '#fffbeb' : '#fef2f2',
                                            borderColor: qualityScore >= 80 ? '#bae6fd' : qualityScore >= 50 ? '#fde68a' : '#fecaca'
                                        }}
                                    >
                                        <p className="text-2xl font-bold" style={{ color: qualityScore >= 80 ? '#0369a1' : qualityScore >= 50 ? '#b45309' : '#dc2626' }}>
                                            {qualityScore ?? '—'}
                                        </p>
                                        <p className="text-xs text-slate-500 font-medium">Quality Score</p>
                                    </div>
                                </div>

                                {/* Matched Typologies */}
                                {matchedTypologies?.length > 0 ? (
                                    matchedTypologies.map((t, idx) => (
                                        <div key={idx} className="bg-white rounded-lg border border-sky-100 overflow-hidden">
                                            <div className="bg-sky-50 px-4 py-3 flex items-center justify-between">
                                                <div className="flex items-center">
                                                    <Target size={16} className="text-sky-600 mr-2" />
                                                    <span className="font-semibold text-sm text-slate-800">{t.name}</span>
                                                </div>
                                                <span className="text-xs font-bold text-white bg-sky-500 px-2 py-0.5 rounded-full">
                                                    {(t.confidence * 100).toFixed(0)}%
                                                </span>
                                            </div>
                                            <div className="px-4 py-3 space-y-2">
                                                <p className="text-xs text-slate-400 font-medium">{t.regulatory_reference}</p>
                                                {t.evidence?.map((e, i) => (
                                                    <div key={i} className="flex items-start text-xs text-slate-600">
                                                        <span className="text-sky-400 mr-2 mt-0.5 flex-shrink-0">•</span>
                                                        <span>{e}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <div className="text-center py-8 text-slate-400 text-sm">
                                        No typology matches detected.
                                    </div>
                                )}

                                {/* Recommendation */}
                                <div className={`rounded-lg p-4 border ${recommendation === 'FILE_SAR' ? 'bg-amber-50 border-amber-200' : 'bg-sky-50 border-sky-200'}`}>
                                    <p className="text-xs font-bold uppercase tracking-wide text-slate-500 mb-1">Recommendation</p>
                                    <p className={`text-lg font-bold ${recommendation === 'FILE_SAR' ? 'text-amber-700' : 'text-sky-700'}`}>
                                        {recommendation || 'Pending...'}
                                    </p>
                                </div>
                            </div>
                        )}

                        {/* Audit Trail Tab */}
                        {activeTab === 'audit' && (
                            <div className="p-5 space-y-4 relative">
                                <div className="absolute left-8 top-5 bottom-5 w-px bg-sky-100"></div>

                                {auditData?.audit_logs?.map((log, idx) => (
                                    <div key={idx} className="relative pl-8">
                                        <div className="absolute left-0 top-1.5 w-5 h-5 bg-white border-2 border-sky-400 rounded-full z-10"></div>
                                        <div className="mb-1">
                                            <span className="text-xs font-bold text-sky-600 uppercase tracking-wider">{log.agent_name}</span>
                                            <span className="text-xs text-slate-400 ml-2">{log.timestamp?.split('T')[1]?.substring(0, 5)}</span>
                                        </div>
                                        <p className="text-sm font-medium text-slate-700">{log.action_type}</p>
                                    </div>
                                ))}

                                {!auditData && (
                                    <div className="text-center py-10 text-slate-400">
                                        <LoaderIcon size={24} className="animate-spin mx-auto mb-2" />
                                        Loading logs...
                                    </div>
                                )}

                                {auditData && (!auditData.audit_logs || auditData.audit_logs.length === 0) && (
                                    <div className="text-center py-10 text-slate-400 text-sm">
                                        No audit logs available.
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

const LoaderIcon = ({ size, className }) => (
    <svg
        xmlns="http://www.w3.org/2000/svg"
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={className}
    >
        <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
);

export default Editor;
