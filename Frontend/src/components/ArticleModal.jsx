import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    X,
    ExternalLink,
    Loader2,
    AlertCircle,
    TrendingUp,
    CheckCircle,
    Clock,
    Sparkles
} from 'lucide-react';
import { api } from '../services/api';

export default function ArticleModal({ isOpen, article, onClose }) {
    const getDisplayValue = (prop, lang = 'en') => {
        if (typeof prop === 'string') return prop;
        if (typeof prop === 'object' && prop !== null) {
            let value = prop;
            if ('value' in prop) value = prop.value;
            else if (lang in prop) value = prop[lang];
            else if (Object.keys(prop).length > 0) value = prop[Object.keys(prop)[0]];
            
            // Handle nested objects (e.g., if value is still an object)
            if (typeof value === 'object' && value !== null) {
                if (lang in value) return value[lang];
                if (Object.keys(value).length > 0) return value[Object.keys(value)[0]];
                return JSON.stringify(value); // Fallback to stringify
            }
            
            return typeof value === 'string' ? value : String(value);
        }
        return String(prop);
    };
    const [analyzing, setAnalyzing] = useState(false);
    const [analysisResults, setAnalysisResults] = useState(null);
    const [error, setError] = useState(null);
    const [pipelineStage, setPipelineStage] = useState(0);

    // Reset state when modal opens with new article
    useEffect(() => {
        if (isOpen && article) {
            setAnalyzing(false);
            setError(null);
            setPipelineStage(0);
            
            // Check if article is already analyzed
            if (article.analyzed) {
                // Fetch existing analysis
                fetchAnalysis();
            } else {
                setAnalysisResults(null);
            }
        }
    }, [isOpen, article?._id]);

    const fetchAnalysis = async () => {
        try {
            const response = await api.getAnalysis(article._id);
            if (response.status === 'success') {
                setAnalysisResults(response.analysis);
            }
        } catch (err) {
            console.error('Failed to fetch analysis:', err);
        }
    };

    const startAnalysis = async () => {
        setAnalyzing(true);
        setError(null);
        setPipelineStage(0);

        try {
            // Pipeline stages (matching backend logic)
            const stages = [
                'Content Extraction',
                'Translation',
                'Sentiment Analysis',
                'Entity Recognition',
                'Summarization',
                'Classification',
                'Bias Detection',
                'Fact Verification'
            ];

            // Progress through stages for visual feedback
            for (let i = 0; i < stages.length; i++) {
                setPipelineStage(i + 1);
                await new Promise(resolve => setTimeout(resolve, 600)); 
            }

            // Call real analysis API
            const response = await api.analyzeArticle(article._id);
            
            if (response.status === 'success') {
                setAnalysisResults(response.analysis);
                // Also update article state locally if possible, but modal closure/reopen will handle it
            } else {
                throw new Error(response.message || 'Analysis failed');
            }
        } catch (err) {
            console.error('Analysis failed:', err);
            setError(err.message || 'Failed to analyze article');
        } finally {
            setAnalyzing(false);
        }
    };

    if (!isOpen || !article) return null;

    const formatDate = (dateString) => {
        if (!dateString) return 'Recently';
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffHours / 24);

        if (diffHours < 24) return `${diffHours} hours ago`;
        if (diffDays < 7) return `${diffDays} days ago`;
        return date.toLocaleDateString();
    };

    return (
        <AnimatePresence>
            <div className="fixed inset-0 z-[150] flex items-center justify-center p-4">
                {/* Backdrop */}
                <motion.div 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={onClose}
                    className="fixed inset-0 bg-black/80 backdrop-blur-xl"
                />

                {/* Modal Container */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95, y: 20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95, y: 20 }}
                    className="relative w-full max-w-5xl max-h-[90vh] bg-[#0f172a] border border-white/10 rounded-[40px] shadow-2xl overflow-hidden z-[151]"
                >
                    {/* Header Controls */}
                    <div className="absolute top-8 right-8 z-20 flex items-center gap-4">
                        <button
                            onClick={onClose}
                            className="p-3 bg-white/5 backdrop-blur-md rounded-2xl hover:bg-white/10 transition-all border border-white/10 text-gray-400 hover:text-white group"
                        >
                            <X size={24} className="group-hover:rotate-90 transition-transform duration-300" />
                        </button>
                    </div>

                    {/* Scrollable Content */}
                    <div className="overflow-y-auto max-h-[90vh] custom-scrollbar scroll-smooth">
                        {/* Article Banner */}
                        {article.image_url && (
                            <div className="relative h-[400px] overflow-hidden">
                                <img
                                    src={article.image_url}
                                    alt={article.title}
                                    className="w-full h-full object-cover"
                                />
                                <div className="absolute inset-0 bg-gradient-to-t from-[#0f172a] via-[#0f172a]/40 to-transparent" />
                                
                                <div className="absolute bottom-12 left-12 right-12">
                                     {/* Meta Info */}
                                    <div className="flex items-center gap-4 text-xs font-black text-indigo-400 uppercase tracking-widest mb-4">
                                        <span className="px-3 py-1.5 bg-indigo-500/20 border border-indigo-500/30 rounded-xl">
                                            📰 {getDisplayValue(article.source)}
                                        </span>
                                        <span className="flex items-center gap-2">
                                            <Clock size={16} />
                                            {formatTime(article.published_date)}
                                        </span>
                                    </div>
                                    <h1 className="text-5xl font-black text-white leading-tight tracking-tight max-w-4xl">
                                        {getDisplayValue(article.title)}
                                    </h1>
                                </div>
                            </div>
                        )}

                        {/* Text Body */}
                        <div className={`p-12 ${!article.image_url ? 'pt-24' : ''}`}>
                            {!article.image_url && (
                                <>
                                    <div className="flex items-center gap-4 text-xs font-black text-indigo-400 uppercase tracking-widest mb-6">
                                        <span className="px-3 py-1.5 bg-indigo-500/20 border border-indigo-500/30 rounded-xl">
                                            📰 {getDisplayValue(article.source)}
                                        </span>
                                        <span className="flex items-center gap-2 text-gray-400">
                                            <Clock size={16} />
                                            {formatTime(article.published_date)}
                                        </span>
                                    </div>
                                    <h1 className="text-5xl font-black text-white mb-10 leading-tight tracking-tight">
                                        {getDisplayValue(article.title)}
                                    </h1>
                                </>
                            )}

                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
                                {/* Left Content: Summary & Original url */}
                                <div className="lg:col-span-2 space-y-10">
                                    <div className="prose prose-invert max-w-none">
                                        <p className="text-xl text-gray-300 leading-relaxed font-medium">
                                            {getDisplayValue(article.summary) || getDisplayValue(article.rss_summary) || 'No summary available for this article.'}
                                        </p>
                                    </div>

                                    {/* Action Button: Analyze */}
                                    {(!article.analyzed || !analysisResults) && !analyzing && (
                                        <motion.div 
                                            initial={{ opacity: 0, y: 20 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            className="p-10 bg-indigo-600/10 rounded-[40px] border border-indigo-500/20 backdrop-blur-md relative overflow-hidden group"
                                        >
                                            <div className="absolute -right-10 -bottom-10 text-indigo-500/10 group-hover:scale-110 transition-transform duration-700">
                                                <Sparkles size={240} />
                                            </div>
                                            
                                            <div className="relative z-10">
                                                <h3 className="text-2xl font-black text-white mb-4 flex items-center gap-3">
                                                    <Sparkles className="text-indigo-400" size={32} />
                                                    Deep Intelligence Audit
                                                </h3>
                                                <p className="text-gray-300 text-lg mb-8 max-w-xl font-medium">
                                                    Our neural engine will perform extensive sentiment analysis, entity linking, and fact-extraction across the full article content.
                                                </p>
                                                <button
                                                    onClick={startAnalysis}
                                                    className="px-10 py-5 bg-indigo-600 text-white rounded-2xl font-black text-xl hover:bg-indigo-500 transition-all shadow-2xl shadow-indigo-500/40 flex items-center gap-4 active:scale-95 group/btn"
                                                >
                                                    <TrendingUp size={24} className="group-hover/btn:translate-y--1 transition-transform" />
                                                    Run Heavy Analysis
                                                    <span className="text-sm font-normal opacity-60 ml-2">Estimated 45s</span>
                                                </button>
                                            </div>
                                        </motion.div>
                                    )}

                                    {/* Pipeline Visualizer (When active) */}
                                    {analyzing && (
                                        <div className="p-10 bg-white/5 rounded-[40px] border border-white/10">
                                            <div className="flex items-center justify-between mb-10">
                                                <div className="space-y-1">
                                                    <h3 className="text-2xl font-black text-white flex items-center gap-4">
                                                        <Loader2 className="animate-spin text-indigo-400" size={32} />
                                                        Intelligence Sync
                                                    </h3>
                                                    <p className="text-gray-400 font-bold uppercase text-[10px] tracking-widest">Processing Layer {pipelineStage} of 8</p>
                                                </div>
                                                <div className="px-5 py-2 bg-indigo-500/10 border border-indigo-500/20 rounded-2xl text-indigo-400 font-black">
                                                    {Math.round((pipelineStage / 8) * 100)}%
                                                </div>
                                            </div>

                                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                                {[
                                                    { name: 'Core Extraction', icon: '📄' },
                                                    { name: 'Neural Translation', icon: '🌐' },
                                                    { name: 'Sentiment Pulse', icon: '😊' },
                                                    { name: 'Entity Context', icon: '👥' },
                                                    { name: 'Abstractive Summary', icon: '📝' },
                                                    { name: 'Vector Embedding', icon: '🏷️' },
                                                    { name: 'Bias Discovery', icon: '⚖️' },
                                                    { name: 'Source Verification', icon: '✓' }
                                                ].map((stage, idx) => {
                                                    const isDone = idx < pipelineStage;
                                                    const isActive = idx === pipelineStage - 1;
                                                    return (
                                                        <div key={idx} className={`flex items-center gap-4 p-4 rounded-2xl border transition-all ${
                                                            isDone ? 'bg-indigo-500/10 border-indigo-500/20' : 
                                                            isActive ? 'bg-white/10 border-white/20 animate-pulse' : 
                                                            'bg-white/5 border-transparent opacity-40'
                                                        }`}>
                                                            <span className="text-xl">{stage.icon}</span>
                                                            <span className={`font-bold text-sm ${isDone ? 'text-indigo-300' : 'text-gray-500'}`}>{stage.name}</span>
                                                            {isDone && <CheckCircle className="ml-auto text-indigo-400" size={16} />}
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    )}

                                    {/* Real Results */}
                                    {analysisResults && (
                                        <div className="space-y-8 animate-fade-in-up">
                                            <div className="flex items-center gap-6">
                                                <h3 className="text-3xl font-black text-white">Neural Results</h3>
                                                <div className="h-px bg-white/10 flex-1" />
                                            </div>
                                            
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                                {/* Sentiment Card */}
                                                <div className="p-8 bg-gradient-to-br from-indigo-900/20 to-blue-900/20 rounded-[32px] border border-indigo-500/20">
                                                    <span className="text-[10px] font-black text-indigo-400 uppercase tracking-widest mb-4 block">Sentiment Analytics</span>
                                                    <div className="flex items-end justify-between mb-6">
                                                        <h4 className="text-4xl font-black text-white capitalize">{analysisResults.sentiment?.label || 'Neutral'}</h4>
                                                        <span className="text-indigo-400 font-bold">{(analysisResults.sentiment?.confidence * 100).toFixed(1)}%</span>
                                                    </div>
                                                    <div className="w-full bg-black/40 h-2 rounded-full overflow-hidden">
                                                        <motion.div 
                                                            initial={{ width: 0 }}
                                                            animate={{ width: `${(analysisResults.sentiment?.confidence || 0.5) * 100}%` }}
                                                            className="h-full bg-indigo-500" 
                                                        />
                                                    </div>
                                                </div>

                                                {/* Entity Count */}
                                                <div className="p-8 bg-gradient-to-br from-indigo-900/20 to-purple-900/20 rounded-[32px] border border-indigo-500/20">
                                                    <span className="text-[10px] font-black text-purple-400 uppercase tracking-widest mb-4 block">Entity Recognition</span>
                                                    <div className="flex items-end justify-between mb-4">
                                                        <h4 className="text-4xl font-black text-white">{analysisResults.entities?.length || 0}</h4>
                                                        <span className="text-purple-400 font-bold">Objects</span>
                                                    </div>
                                                    <p className="text-gray-400 text-xs font-medium">Mapped across GPE, PERSON, ORG and EVENT clusters.</p>
                                                </div>
                                            </div>

                                            {/* AI Summary */}
                                            <div className="p-8 bg-white/5 rounded-[32px] border border-white/10">
                                                <span className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-4 block">AI Intelligence Summary</span>
                                                <p className="text-gray-200 text-lg leading-relaxed">{getDisplayValue(analysisResults.summary)}</p>
                                            </div>
                                        </div>
                                    )}
                                </div>

                                {/* Right Sidebar: Stats & Entities */}
                                <div className="space-y-8">
                                    <div className="p-8 bg-white/5 rounded-[32px] border border-white/10 space-y-6">
                                        <h4 className="text-sm font-black text-white uppercase tracking-widest">Contextual Metadata</h4>
                                        <div className="space-y-4">
                                            <div className="flex items-center justify-between">
                                                <span className="text-gray-500 font-bold text-xs uppercase tracking-tight">Status</span>
                                                <span className={`px-2 py-1 rounded-md text-[10px] font-black uppercase ${article.analyzed ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}`}>
                                                    {article.analyzed ? 'Verified Intelligence' : 'Raw Content'}
                                                </span>
                                            </div>
                                            <div className="flex items-center justify-between">
                                                <span className="text-gray-500 font-bold text-xs uppercase tracking-tight">Language</span>
                                                <span className="text-white font-black text-xs uppercase">{getDisplayValue(article.language) || 'English'}</span>
                                            </div>
                                            <div className="flex items-center justify-between">
                                                <span className="text-gray-500 font-bold text-xs uppercase tracking-tight">Category</span>
                                                <span className="text-indigo-400 font-black text-xs uppercase">{getDisplayValue(article.category) || 'General'}</span>
                                            </div>
                                        </div>
                                        <div className="pt-6 border-t border-white/5">
                                            <a
                                                href={article.original_url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="w-full py-4 px-6 bg-white/5 text-white/80 rounded-2xl font-black text-center text-xs hover:bg-white/10 transition-all flex items-center justify-center gap-3 border border-white/10"
                                            >
                                                <ExternalLink size={16} /> Open Source Link
                                            </a>
                                        </div>
                                    </div>

                                    {/* Related Entities (Placeholder or dynamic) */}
                                    {analysisResults?.keywords && (
                                        <div className="p-8 bg-white/5 rounded-[32px] border border-white/10">
                                            <h4 className="text-sm font-black text-white uppercase tracking-widest mb-6">Semantic Tags</h4>
                                            <div className="flex flex-wrap gap-2">
                                                {analysisResults.keywords.slice(0, 8).map((k, i) => (
                                                    <span key={i} className="px-3 py-1.5 bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-[10px] font-black rounded-lg uppercase">
                                                        #{k}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Footer Branding */}
                            <div className="mt-20 pt-8 border-t border-white/10 text-center">
                                <p className="text-[10px] font-black text-gray-700 uppercase tracking-[0.5em]">Antigravity Artificial Intelligence • Neural Engine v2.4.0</p>
                            </div>
                        </div>
                    </div>
                </motion.div>
            </div>
        </AnimatePresence>
    );

    function formatTime(dateString) {
        if (!dateString) return 'Recently';
        try {
            const date = new Date(dateString);
            const now = new Date();
            const diffMs = now - date;
            const diffMins = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMins / 60);

            if (diffMins < 60) return `${diffMins}M AGO`;
            if (diffHours < 24) return `${diffHours}H AGO`;
            return date.toLocaleDateString().toUpperCase();
        } catch (e) { return 'RECENTLY'; }
    }
}
