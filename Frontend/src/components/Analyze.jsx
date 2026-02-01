import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    BarChart3,
    FileText,
    Target,
    ChevronRight,
    ChevronLeft,
    Menu,
    LayoutDashboard,
    FileSearch,
    PieChart,
    Globe,
    Upload,
    X,
    Loader2,
    Activity,
    Smile,
    Frown,
    Sparkles,
    History,
    Clock
} from 'lucide-react';

import SentimentAnalysis from './SentimentAnalysis';
import Translation from './Translation';
import Summarization from './Summarization';
import KeywordExtraction from './KeywordExtraction';
import DocumentList from './DocumentList';
import AnalyticsReports from './AnalyticsReports';
import DetailedStats from './DetailedStats';
import AnalysisCard from './AnalysisCard';
import { api } from '../services/api';

const sidebarItems = [
    { id: 'upload', label: 'Upload Document', icon: <Upload size={20} />, component: (props) => <AnalysisCard {...props} /> },
    { id: 'documents', label: 'List of Documents', icon: <FileSearch size={20} />, component: (props) => <DocumentList {...props} /> },
    { id: 'sentiment', label: 'Sentiment Analysis', icon: <BarChart3 size={20} />, component: (props) => <SentimentAnalysis {...props} /> },
    { id: 'translation', label: 'Translation', icon: <Globe size={20} />, component: (props) => <Translation {...props} /> },
    { id: 'summary', label: 'Summary', icon: <FileText size={20} />, component: (props) => <Summarization {...props} /> },
    { id: 'keywords', label: 'Keyword Extraction', icon: <Target size={20} />, component: (props) => <KeywordExtraction {...props} /> },
    { id: 'analytics', label: 'Analytics Dashboard', icon: <PieChart size={20} />, component: (props) => <AnalyticsReports {...props} /> },
    { id: 'detailed-stats', label: 'Detailed Statistics', icon: <LayoutDashboard size={20} />, component: (props) => <DetailedStats {...props} /> },
];

export default function Analyze() {
    const [activeTab, setActiveTab] = useState(() => {
        return localStorage.getItem('analyzeActiveTab') || 'upload';
    });

    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

    // Translation / Toggle State
    const [displayMode, setDisplayMode] = useState('english'); // 'english' | 'native'
    const [isTranslating, setIsTranslating] = useState(false);
    
    // Global Analysis Modal State
    const [selectedDocAnalysis, setSelectedDocAnalysis] = useState(null);
    const [isAnalysisLoading, setIsAnalysisLoading] = useState(false);
    const [analysisData, setAnalysisData] = useState(null);

    const handleTabChange = (tabId) => {
        setActiveTab(tabId);
        localStorage.setItem('analyzeActiveTab', tabId);
    };

    const handleAnalysisClick = async (doc) => {
        setSelectedDocAnalysis(doc);
        setIsAnalysisLoading(true);
        setAnalysisData(null);
        setDisplayMode('english'); // Reset to English by default

        try {
            const [sentiment, summary, keywords] = await Promise.allSettled([
                api.analyzeSentiment(doc.document_id),
                api.generateSummary(doc.document_id),
                api.extractKeywords(doc.document_id)
            ]);

            setAnalysisData({
                sentiment: sentiment.status === 'fulfilled' && sentiment.value?.status === 'success' ? sentiment.value.data : null,
                summary: summary.status === 'fulfilled' && summary.value?.status === 'success' ? summary.value.data : null,
                keywords: keywords.status === 'fulfilled' && keywords.value?.status === 'success' ? keywords.value.data : null
            });
        } catch (err) {
            console.error('Failed to load analysis:', err);
            setAnalysisData({
                sentiment: null,
                summary: null,
                keywords: null
            });
        } finally {
            setIsAnalysisLoading(false);
        }
    };

    return (
        <div className="flex min-h-[calc(100vh-80px)] pt-20 relative z-10 transition-all duration-300">
            {/* Sidebar */}
            <motion.aside
                initial={false}
                animate={{ width: isSidebarCollapsed ? 96 : 288 }}
                className="bg-[#0f172a]/40 backdrop-blur-xl border-r border-white/10 p-4 space-y-6 fixed top-20 min-h-[calc(100vh-80px)] z-20"
            >
                {/* Toggle Button */}
                <div className="flex items-center justify-between px-2 mb-4">
                    {!isSidebarCollapsed && (
                        <p className="text-[10px] font-black text-indigo-400 uppercase tracking-widest pl-2">Dashboard</p>
                    )}
                    <button
                        onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
                        className="p-3 rounded-xl bg-white/5 border border-white/10 text-indigo-400 hover:bg-indigo-600 hover:text-white transition-all shadow-lg hover:shadow-indigo-500/20 active:scale-90"
                    >
                        {isSidebarCollapsed ? <Menu size={20} /> : <ChevronLeft size={20} />}
                    </button>
                </div>

                <nav className="space-y-1">
                    {sidebarItems.slice(0, 6).map((item) => (
                        <button
                            key={item.id}
                            onClick={() => handleTabChange(item.id)}
                            className={`w-full flex items-center gap-3 px-4 py-4 rounded-xl transition-all font-semibold relative group ${activeTab === item.id
                                ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20'
                                : 'text-gray-400 hover:bg-white/5 hover:text-white'
                                }`}
                            title={isSidebarCollapsed ? item.label : ''}
                        >
                            <div className={`flex items-center gap-3 ${isSidebarCollapsed ? 'mx-auto' : ''}`}>
                                {item.icon}
                                {!isSidebarCollapsed && (
                                    <motion.span
                                        initial={{ opacity: 0, x: -10 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        className="whitespace-nowrap"
                                    >
                                        {item.label}
                                    </motion.span>
                                )}
                            </div>
                            {!isSidebarCollapsed && activeTab === item.id && <ChevronRight size={16} />}

                            {/* Tooltip for collapsed state */}
                            {isSidebarCollapsed && (
                                <div className="absolute left-full ml-4 px-3 py-2 bg-indigo-600 text-white text-xs font-bold rounded-lg opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto transition-opacity whitespace-nowrap z-50 shadow-xl shadow-indigo-500/20">
                                    {item.label}
                                </div>
                            )}
                        </button>
                    ))}
                </nav>

                <div className="pt-8 mt-4 border-t border-white/5 space-y-4">
                    {!isSidebarCollapsed && (
                        <p className="px-4 text-[10px] font-black text-indigo-400 uppercase tracking-widest">Other Reports</p>
                    )}
                    <button
                        onClick={() => handleTabChange('analytics')}
                        className={`w-full flex items-center gap-3 px-4 py-4 rounded-xl transition-all font-semibold relative group ${activeTab === 'analytics'
                            ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20'
                            : 'text-gray-400 hover:bg-white/5 hover:text-white'
                            }`}
                        title={isSidebarCollapsed ? 'Analytics' : ''}
                    >
                        <div className={`flex items-center gap-3 ${isSidebarCollapsed ? 'mx-auto' : ''}`}>
                            <PieChart size={20} />
                            {!isSidebarCollapsed && (
                                <motion.span
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    className="whitespace-nowrap"
                                >
                                    Analytics
                                </motion.span>
                            )}
                        </div>
                        {!isSidebarCollapsed && activeTab === 'analytics' && <ChevronRight size={16} />}

                        {isSidebarCollapsed && (
                            <div className="absolute left-full ml-4 px-3 py-2 bg-indigo-600 text-white text-xs font-bold rounded-lg opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto transition-opacity whitespace-nowrap z-50 shadow-xl shadow-indigo-500/20">
                                Analytics
                            </div>
                        )}
                    </button>
                    <button
                        onClick={() => handleTabChange('detailed-stats')}
                        className={`w-full flex items-center gap-3 px-4 py-4 rounded-xl transition-all font-semibold relative group ${activeTab === 'detailed-stats'
                            ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20'
                            : 'text-gray-400 hover:bg-white/5 hover:text-white'
                            }`}
                        title={isSidebarCollapsed ? 'Detailed Stats' : ''}
                    >
                        <div className={`flex items-center gap-3 ${isSidebarCollapsed ? 'mx-auto' : ''}`}>
                            <LayoutDashboard size={20} />
                            {!isSidebarCollapsed && (
                                <motion.span
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    className="whitespace-nowrap"
                                >
                                    Detailed Stats
                                </motion.span>
                            )}
                        </div>
                        {!isSidebarCollapsed && activeTab === 'detailed-stats' && <ChevronRight size={16} />}

                        {isSidebarCollapsed && (
                            <div className="absolute left-full ml-4 px-3 py-2 bg-indigo-600 text-white text-xs font-bold rounded-lg opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto transition-opacity whitespace-nowrap z-50 shadow-xl shadow-indigo-500/20">
                                Detailed Stats
                            </div>
                        )}
                    </button>
                </div>
            </motion.aside>

            {/* Content Area */}
            <motion.main
                animate={{ marginLeft: isSidebarCollapsed ? 96 : 288 }}
                className="flex-1 p-10 pt-8 min-h-screen transition-all duration-300"
            >
                <div className="max-w-6xl mx-auto">
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={activeTab}
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -20 }}
                            transition={{ duration: 0.3 }}
                        >
                            {sidebarItems.find(item => item.id === activeTab)?.component({
                                onNavigate: handleTabChange,
                                onAnalysisClick: handleAnalysisClick // Pass the trigger down
                            })}
                        </motion.div>
                    </AnimatePresence>
                </div>
            </motion.main>

            {/* Global Analysis Results Modal */}
            <AnimatePresence>
                {selectedDocAnalysis && (
                    <div className="fixed inset-0 z-[100] flex items-center justify-center p-6 md:p-12 lg:p-20 overflow-hidden">
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setSelectedDocAnalysis(null)}
                            className="absolute inset-0 bg-gray-950/80 backdrop-blur-md"
                        />
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0, y: 40 }}
                            animate={{ scale: 1, opacity: 1, y: 0 }}
                            exit={{ scale: 0.9, opacity: 0, y: 40 }}
                            className="bg-[#0f172a]/95 backdrop-blur-2xl rounded-[48px] shadow-2xl w-full max-w-5xl max-h-[85vh] overflow-hidden relative z-10 border border-white/10 flex flex-col highlight-white/5"
                        >
                            {/* Modal Header */}
                            <div className="p-10 border-b border-white/5 flex items-center justify-between bg-white/5">
                                <div className="flex items-center gap-6">
                                    <div className="w-16 h-16 bg-indigo-500/10 rounded-2xl flex items-center justify-center text-indigo-400 border border-indigo-500/20 shadow-inner">
                                        <BarChart3 size={32} />
                                    </div>
                                    <div className="space-y-1">
                                        <h3 className="text-3xl font-black text-white leading-none tracking-tight">Intelligence Audit</h3>
                                        <p className="text-xs font-bold text-gray-500 uppercase tracking-[0.25em]">{selectedDocAnalysis.filename}</p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-4">
                                     {/* Language Toggle */}
                                     {analysisData?.language && analysisData.language !== 'en' && (
                                        <div className="bg-white/5 p-1 rounded-xl border border-white/10 flex items-center">
                                            <button
                                                onClick={() => setDisplayMode('native')}
                                                className={`px-4 py-2 rounded-lg text-xs font-black uppercase tracking-widest transition-all ${displayMode === 'native' ? 'bg-indigo-600 text-white shadow-lg' : 'text-gray-500 hover:text-white'}`}
                                            >
                                                Native ({analysisData.language})
                                            </button>
                                            <button
                                                onClick={() => setDisplayMode('english')}
                                                className={`px-4 py-2 rounded-lg text-xs font-black uppercase tracking-widest transition-all ${displayMode === 'english' ? 'bg-indigo-600 text-white shadow-lg' : 'text-gray-500 hover:text-white'}`}
                                            >
                                                English
                                            </button>
                                        </div>
                                     )}
                                    <button
                                        onClick={() => setSelectedDocAnalysis(null)}
                                        className="p-4 bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white rounded-2xl transition-all border border-white/10 group"
                                    >
                                        <X size={28} className="group-hover:rotate-90 transition-transform duration-300" />
                                    </button>
                                </div>
                            </div>

                            {/* Modal Content */}
                            <div className="flex-1 overflow-y-auto p-10 custom-scrollbar">
                                {isAnalysisLoading ? (
                                    <div className="h-96 flex flex-col items-center justify-center gap-4">
                                        <div className="relative">
                                            <Loader2 size={64} className="animate-spin text-indigo-500/20" />
                                            <Loader2 size={64} className="animate-spin text-indigo-500 absolute inset-0 [animation-delay:-0.5s]" />
                                        </div>
                                        <p className="text-gray-400 font-black uppercase tracking-[0.2em] text-sm animate-pulse">Scanning Document Core...</p>
                                    </div>
                                ) : analysisData ? (
                                    <div className="space-y-12 animate-fade-in">
                                        {/* Sentiment Section */}
                                        <section className="space-y-6">
                                            <div className="flex items-center gap-3">
                                                <Activity size={20} className="text-emerald-400" />
                                                <h4 className="font-black text-white uppercase tracking-wider text-sm">Sentiment Verdict</h4>
                                            </div>
                                            <div className="grid md:grid-cols-3 gap-6">
                                                <div className="p-6 bg-white/5 rounded-3xl border border-white/10 flex flex-col justify-center relative overflow-hidden group">
                                                    <div className={`absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity`}>
                                                        {analysisData.sentiment?.sentiment === 'positive' ? <Smile size={80} /> : <Frown size={80} />}
                                                    </div>
                                                    <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-2">Overall Sentiment</p>
                                                    <p className={`text-3xl font-black capitalize ${analysisData.sentiment?.sentiment === 'positive' ? 'text-emerald-400' : 'text-red-400'}`}>
                                                        {analysisData.sentiment?.sentiment}
                                                    </p>
                                                    <p className="text-xs font-bold text-gray-500 mt-1">{(analysisData.sentiment?.confidence * 100).toFixed(1)}% Confidence</p>
                                                </div>
                                                <div className="col-span-2 p-6 bg-white/5 rounded-3xl border border-white/10">
                                                    <div className="space-y-4">
                                                        {Object.entries(analysisData.sentiment?.scores || {}).map(([key, value]) => (
                                                            <div key={key}>
                                                                <div className="flex justify-between text-[10px] font-black uppercase tracking-widest mb-1">
                                                                    <span className={key === 'positive' ? 'text-emerald-400' : key === 'negative' ? 'text-red-400' : 'text-indigo-400'}>{key}</span>
                                                                    <span className="text-white">{(value * 100).toFixed(1)}%</span>
                                                                </div>
                                                                <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden border border-white/5">
                                                                    <motion.div
                                                                        initial={{ width: 0 }}
                                                                        animate={{ width: `${(value || 0) * 100}%` }}
                                                                        className={`h-full rounded-full ${key === 'positive' ? 'bg-emerald-500' : key === 'negative' ? 'bg-red-500' : 'bg-indigo-500'}`}
                                                                    />
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            </div>
                                        </section>

                                        {/* Summary Section */}
                                        <section className="space-y-6">
                                            <div className="flex items-center gap-3">
                                                <Sparkles size={20} className="text-indigo-400" />
                                                <h4 className="font-black text-white uppercase tracking-wider text-sm">
                                                    Executive Summary {displayMode === 'native' ? `(${analysisData.language})` : '(English)'}
                                                </h4>
                                            </div>
                                            <div className="p-8 bg-indigo-500/5 rounded-[40px] border border-indigo-500/10 relative overflow-hidden group">
                                                <div className="absolute -right-10 -bottom-10 opacity-[0.03] group-hover:scale-110 transition-transform duration-700">
                                                    <Sparkles size={200} />
                                                </div>
                                                <p className="text-lg text-indigo-50 font-medium leading-relaxed">
                                                    {displayMode === 'english' 
                                                        ? (analysisData.summary?.summary?.en || analysisData.summary?.summary || "No summary available.")
                                                        : (analysisData.summary?.summary?.text || analysisData.summary?.summary || "No native summary available.")}
                                                </p>
                                                <div className="mt-8 flex gap-6">
                                                    <div className="flex items-center gap-2">
                                                        <History size={14} className="text-indigo-400" />
                                                        <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest">{analysisData.summary?.stats?.reduction_percentage || 0}% Reduction</span>
                                                    </div>
                                                    <div className="flex items-center gap-2">
                                                        <Clock size={14} className="text-indigo-400" />
                                                        <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest">{analysisData.summary?.stats?.time_taken || 0}s Process Time</span>
                                                    </div>
                                                </div>
                                            </div>
                                        </section>

                                        {/* Keywords Section */}
                                        <section className="space-y-6">
                                            <div className="flex items-center gap-3">
                                                <Target size={20} className="text-purple-400" />
                                                <h4 className="font-black text-white uppercase tracking-wider text-sm">Keyword Cloud</h4>
                                            </div>
                                            <div className="flex flex-wrap gap-3">
                                                {(displayMode === 'english' ? (analysisData.keywords?.keywords?.en || []) : (analysisData.keywords?.keywords?.native || analysisData.keywords?.keywords || [])).map((kw, i) => (
                                                    <motion.div
                                                        key={i}
                                                        initial={{ scale: 0.9, opacity: 0 }}
                                                        animate={{ scale: 1, opacity: 1 }}
                                                        transition={{ delay: i * 0.05 }}
                                                        className={`px-6 py-3 rounded-2xl font-bold text-sm bg-white/5 border border-white/10 text-gray-300 hover:bg-white/10 hover:border-indigo-500/30 hover:text-indigo-300 transition-all cursor-default`}
                                                    >
                                                        {kw.text}
                                                        <span className="ml-2 text-[10px] opacity-30">#{kw.rank}</span>
                                                    </motion.div>
                                                ))}
                                            </div>
                                        </section>
                                    </div>
                                ) : null}
                            </div>

                            {/* Modal Footer */}
                            <div className="p-10 border-t border-white/5 flex items-center justify-between bg-white/5">
                                <p className="text-[10px] font-black text-gray-500 uppercase tracking-[2px]">InsightPoint Neural Engine v2.0</p>
                                <button
                                    onClick={() => setSelectedDocAnalysis(null)}
                                    className="px-10 py-4 bg-indigo-600 text-white font-black rounded-2xl hover:brightness-110 active:scale-95 transition-all shadow-xl shadow-indigo-900/30"
                                >
                                    Dismiss Audit
                                </button>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </div>
    );
}
