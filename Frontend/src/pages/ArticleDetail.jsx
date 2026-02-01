import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
    ArrowLeft,
    ExternalLink,
    Loader2,
    AlertCircle,
    TrendingUp,
    CheckCircle,
    Clock,
    Sparkles
} from 'lucide-react';
import { api } from '../services/api';

export default function ArticleDetail() {
    const { id } = useParams();
    const navigate = useNavigate();

    const [article, setArticle] = useState(null);
    const [loading, setLoading] = useState(true);
    const [analyzing, setAnalyzing] = useState(false);
    const [analysisResults, setAnalysisResults] = useState(null);
    const [error, setError] = useState(null);
    const [showEnglish, setShowEnglish] = useState(true); // Toggle for English/Original language
    const [expandedGroups, setExpandedGroups] = useState({}); // Track which entity groups are expanded

    const [pipelineStatus, setPipelineStatus] = useState({
        progress: 0,
        current_stage: 'Initializing...',
        stages: []
    });

    // Fetch article details on mount
    useEffect(() => {
        fetchArticle();

        let pollInterval;
        if (analyzing) {
            // Poll for pipeline status every 3 seconds (reduced from 2s)
            pollInterval = setInterval(async () => {
                try {
                    const statusRes = await api.getPipelineStatus(id);
                    if (statusRes.status === 'success') {
                        setPipelineStatus(statusRes.data);
                        
                        // When analysis completes, fetch results and stop polling
                        if (statusRes.data.progress === 100) {
                            clearInterval(pollInterval);
                            setAnalyzing(false);
                            
                            // Fetch analysis results (article data is already updated by backend)
                            await fetchAnalysis();
                        }
                    }
                } catch (err) {
                    console.error('Polling failed:', err);
                    // Stop polling on error to prevent infinite failed requests
                    clearInterval(pollInterval);
                    setAnalyzing(false);
                }
            }, 3000); // Increased from 2000ms to 3000ms
        }

        return () => {
            if (pollInterval) clearInterval(pollInterval);
        };
    }, [id, analyzing]);

    const fetchArticle = async () => {
        setLoading(true);
        try {
            const response = await api.getArticle(id);
            if (response.status === 'success') {
                setArticle(response.article);

                // Check if already analyzed
                if (response.article?.analyzed) {
                    fetchAnalysis();
                }
                
                // Auto-fetch removed to prevent unwanted API calls
                // If the user wants to see analysis, they will click the button
            } else {
                setError('Article not found');
            }
        } catch (err) {
            console.error('Failed to fetch article:', err);
            setError('Failed to load article');
        } finally {
            setLoading(false);
        }
    };

    const fetchAnalysis = async () => {
        try {
            const response = await api.getAnalysis(id);
            if (response.status === 'success') {
                console.log('📊 Existing Analysis Response:', response);

                // Merge summary and translation from root if they exist
                const fullAnalysis = {
                    ...response.analysis,
                    summary: response.summary || response.analysis?.summary,
                    analysis_translated: response.analysis_translated || response.translated
                };

                setAnalysisResults(fullAnalysis);
            }
        } catch (err) {
            console.error('Failed to fetch analysis:', err);
        }
    };

    const startAnalysis = async () => {
        setAnalyzing(true);
        setError(null);
        setPipelineStatus({
            progress: 0,
            current_stage: 'Starting analysis...',
            stages: []
        });

        try {
            // Trigger analysis (non-blocking in some backend impls, but here we wait for the trigger)
            await api.analyzeArticle(id);
            // Polling is handled by useEffect
        } catch (err) {
            console.error('Analysis trigger failed:', err);
            setError(err.message || 'Failed to start analysis');
            setAnalyzing(false);
        }
    };

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

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <Loader2 className="animate-spin text-indigo-400" size={48} />
            </div>
        );
    }

    if (!article) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <AlertCircle size={48} className="text-red-400 mx-auto mb-4" />
                    <h2 className="text-2xl font-black text-white mb-2">Article Not Found</h2>
                    <button
                        onClick={() => navigate('/')}
                        className="mt-4 px-6 py-3 bg-indigo-600 text-white rounded-xl font-bold hover:bg-indigo-500 transition-all"
                    >
                        Back to News Feed
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen pb-20">
            {/* Header with Back Button */}
            <div className="sticky top-0 z-20 bg-[#0f172a]/80 backdrop-blur-xl border-b border-white/10">
                <div className="max-w-6xl mx-auto px-6 py-4">
                    <button
                        onClick={() => navigate('/')}
                        className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors font-bold"
                    >
                        <ArrowLeft size={20} />
                        Back to News Feed
                    </button>
                </div>
            </div>

            {/* Article Content */}
            <div className="max-w-6xl mx-auto px-6 py-12">
                {/* Hero Image */}
                {article.image_url && (
                    <div className="relative h-[500px] rounded-[40px] overflow-hidden mb-12 shadow-2xl shadow-black/50 border border-white/5">
                        <img
                            src={article.image_url}
                            alt={article.title}
                            className="w-full h-full object-cover"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-[#0f172a] via-transparent to-transparent opacity-80" />
                    </div>
                )}

                {/* Meta Info */}
                <div className="flex items-center gap-4 text-gray-400 font-bold mb-6">
                    <span className="flex items-center gap-2">
                        📰 {article.source}
                    </span>
                    <span>•</span>
                    <span className="flex items-center gap-2">
                        <Clock size={16} />
                        {formatDate(article.published_date)}
                    </span>
                    {article.category && (
                        <>
                            <span>•</span>
                            <span className="px-3 py-1 bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded-full text-sm font-black uppercase tracking-wider">
                                {article.category}
                            </span>
                        </>
                    )}
                </div>

                {/* Title */}
                <h1 className="text-5xl font-black text-white mb-8 leading-tight tracking-tight">
                    {article.title}
                </h1>

                {/* Summary */}
                {article.summary && (
                    <p className="text-xl text-gray-300 mb-12 leading-relaxed">
                        {article.summary}
                    </p>
                )}

                {/* Analysis Section */}
                {(!article.analyzed || !analysisResults) && !analyzing && (
                    <div className="mb-12 p-8 bg-white/5 rounded-3xl border border-white/10 backdrop-blur-sm">
                        <div className="flex items-start gap-6">
                            <div className="p-4 bg-indigo-500/20 rounded-2xl border border-indigo-500/30">
                                <Sparkles size={32} className="text-indigo-400" />
                            </div>
                            <div className="flex-1">
                                <h3 className="text-2xl font-black text-white mb-3">
                                    Get AI-Powered Deep Analysis
                                </h3>
                                <p className="text-gray-400 mb-6 text-lg">
                                    Run our advanced NLP pipeline to get comprehensive sentiment analysis, key entities, location extraction, event classification, and more.
                                </p>
                                <button
                                    onClick={startAnalysis}
                                    className="px-8 py-4 bg-indigo-600 text-white rounded-2xl font-black hover:bg-indigo-500 transition-all shadow-lg shadow-indigo-500/20 flex items-center gap-3"
                                >
                                    <Sparkles size={20} />
                                    Run Deep Analysis
                                    <span className="text-sm font-normal opacity-80">~60 seconds</span>
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {analyzing && (
                    <div className="mb-12 p-8 bg-white/5 rounded-3xl border border-white/10 backdrop-blur-sm">
                        <div className="flex items-center justify-between mb-8">
                            <h3 className="text-2xl font-black text-white flex items-center gap-3">
                                <Loader2 className="animate-spin text-indigo-400" size={28} />
                                {pipelineStatus.current_stage || 'Analyzing Article...'}
                            </h3>
                            <span className="px-4 py-2 bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 rounded-xl font-black text-sm">
                                {pipelineStatus.progress}% Complete
                            </span>
                        </div>

                        {/* Progress Bar */}
                        <div className="w-full bg-white/5 rounded-full h-4 mb-8 overflow-hidden">
                            <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${pipelineStatus.progress}%` }}
                                className="h-full bg-gradient-to-r from-indigo-500 to-blue-500 transition-all duration-500"
                            />
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {(pipelineStatus.stages?.length > 0 ? pipelineStatus.stages : [
                                { id: 'deduplication', label: 'Deduplication', status: 'pending' },
                                { id: 'scraping', label: 'Deep Scraping', status: 'pending' },
                                { id: 'translation', label: 'Multi-Lingual Translation', status: 'pending' },
                                { id: 'summarization', label: 'AI Summarization', status: 'pending' },
                                { id: 'keywords', label: 'Keyword Extraction', status: 'pending' },
                                { id: 'ner', label: 'Named Entity Recognition', status: 'pending' },
                                { id: 'location', label: 'Geo-Location Mapping', status: 'pending' },
                                { id: 'sentiment', label: 'Sentiment Analysis', status: 'pending' }
                            ]).map((stage, index) => {
                                const isComplete = stage.status === 'completed';
                                const isActive = stage.status === 'processing';
                                const isError = stage.status === 'error';
                                const isPending = stage.status === 'pending';

                                const stageIcons = {
                                    'deduplication': '🔍',
                                    'scraping': '📄',
                                    'translation': '🌐',
                                    'summarization': '📝',
                                    'keywords': '🔑',
                                    'ner': '👥',
                                    'location': '📍',
                                    'sentiment': '😊'
                                };

                                return (
                                    <motion.div
                                        key={stage.id}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: index * 0.05 }}
                                        className={`flex items-center gap-4 p-4 rounded-2xl transition-all border ${isComplete ? 'bg-green-500/10 border-green-500/20' :
                                                isActive ? 'bg-indigo-500/10 border-indigo-500/30 shadow-[0_0_15px_rgba(99,102,241,0.1)]' :
                                                    isError ? 'bg-red-500/10 border-red-500/20' :
                                                        'bg-white/5 border-white/5 opacity-60'
                                            }`}
                                    >
                                        <div className="text-2xl">{stageIcons[stage.id] || '⚙️'}</div>
                                        <div className="flex-1">
                                            <p className={`font-bold text-sm ${isComplete ? 'text-green-400' :
                                                    isActive ? 'text-indigo-300' :
                                                        isError ? 'text-red-400' :
                                                            'text-gray-500'
                                                }`}>
                                                {stage.label}
                                            </p>
                                        </div>
                                        {isComplete && <CheckCircle size={18} className="text-green-500" />}
                                        {isActive && <Loader2 size={18} className="animate-spin text-indigo-400" />}
                                        {isError && <AlertCircle size={18} className="text-red-500" />}
                                        {isPending && <Clock size={18} className="text-gray-600" />}
                                    </motion.div>
                                );
                            })}
                        </div>
                    </div>
                )}

                {/* Analysis Results */}
                {analysisResults && (
                    <div className="mb-12 space-y-8">
                        <div className="flex items-center justify-between">
                            <h3 className="text-3xl font-black text-white flex items-center gap-3">
                                <TrendingUp className="text-indigo-400" size={32} />
                                Analysis Results
                            </h3>

                            {/* Language Toggle */}
                            {(analysisResults.analysis_translated || analysisResults.translated) && (
                                <button
                                    onClick={() => setShowEnglish(!showEnglish)}
                                    className="flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 rounded-2xl font-bold text-gray-300 hover:bg-white/10 hover:text-white transition-all shadow-sm"
                                >
                                    <span className="text-2xl">{showEnglish ? '🇬🇧' : '🌍'}</span>
                                    <span>{showEnglish ? 'English' : 'Original'}</span>
                                    <svg className={`w-4 h-4 transition-transform duration-300 ${!showEnglish ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                                    </svg>
                                </button>
                            )}
                        </div>

                        {/* Sentiment */}
                        {analysisResults.sentiment && (
                            <motion.div
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="p-8 bg-gradient-to-br from-purple-900/20 to-pink-900/20 rounded-3xl border border-purple-500/20 backdrop-blur-md"
                            >
                                <h4 className="text-2xl font-black text-white mb-6">😊 Sentiment Analysis</h4>
                                <div className="space-y-6">
                                    <div className="flex items-center justify-between">
                                        <span className="font-bold text-gray-300 text-lg">Overall Sentiment</span>
                                        <span className="text-2xl font-black text-purple-400 capitalize">
                                            {analysisResults.sentiment.label || 'Neutral'}
                                        </span>
                                    </div>

                                    {/* Sentiment Scores */}
                                    {analysisResults.sentiment.scores && (
                                        <div className="space-y-3">
                                            <div>
                                                <div className="flex justify-between mb-1">
                                                    <span className="text-sm font-bold text-green-400">Positive</span>
                                                    <span className="text-sm font-bold text-green-400">
                                                        {(analysisResults.sentiment.scores.pos * 100).toFixed(1)}%
                                                    </span>
                                                </div>
                                                <div className="w-full bg-black/40 rounded-full h-3">
                                                    <div
                                                        className="bg-gradient-to-r from-green-400 to-green-600 h-3 rounded-full transition-all"
                                                        style={{ width: `${analysisResults.sentiment.scores.pos * 100}%` }}
                                                    />
                                                </div>
                                            </div>

                                            <div>
                                                <div className="flex justify-between mb-1">
                                                    <span className="text-sm font-bold text-gray-400">Neutral</span>
                                                    <span className="text-sm font-bold text-gray-400">
                                                        {(analysisResults.sentiment.scores.neu * 100).toFixed(1)}%
                                                    </span>
                                                </div>
                                                <div className="w-full bg-black/40 rounded-full h-3">
                                                    <div
                                                        className="bg-gradient-to-r from-gray-400 to-gray-600 h-3 rounded-full transition-all"
                                                        style={{ width: `${analysisResults.sentiment.scores.neu * 100}%` }}
                                                    />
                                                </div>
                                            </div>

                                            <div>
                                                <div className="flex justify-between mb-1">
                                                    <span className="text-sm font-bold text-red-400">Negative</span>
                                                    <span className="text-sm font-bold text-red-400">
                                                        {(analysisResults.sentiment.scores.neg * 100).toFixed(1)}%
                                                    </span>
                                                </div>
                                                <div className="w-full bg-black/40 rounded-full h-3">
                                                    <div
                                                        className="bg-gradient-to-r from-red-400 to-red-600 h-3 rounded-full transition-all"
                                                        style={{ width: `${analysisResults.sentiment.scores.neg * 100}%` }}
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    <div className="flex items-center justify-between text-sm text-gray-500 pt-4 border-t border-purple-500/20">
                                        <span>Confidence: {(analysisResults.sentiment.confidence * 100).toFixed(1)}%</span>
                                        <span>Method: {analysisResults.sentiment.method}</span>
                                    </div>
                                </div>
                            </motion.div>
                        )}

                        {/* Summary */}
                        {analysisResults.summary && (
                            <motion.div
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.1 }}
                                className="p-8 bg-gradient-to-br from-blue-900/20 to-cyan-900/20 rounded-3xl border border-blue-500/20 backdrop-blur-md"
                            >
                                <h4 className="text-2xl font-black text-white mb-6">📝 AI Summary</h4>

                                {/* Display summary based on language toggle */}
                                {(() => {
                                    let summaryText = '';
                                    const translatedObj = analysisResults.analysis_translated || analysisResults.translated;
                                    const targetLang = translatedObj ? Object.keys(translatedObj)[0] : null;

                                    // Check if we have translated analysis
                                    if (translatedObj && targetLang) {
                                        if (showEnglish) {
                                            // Show English summary
                                            summaryText = analysisResults.summary?.text || analysisResults.summary;
                                        } else {
                                            // Show original language summary from translated object
                                            const transSummary = translatedObj[targetLang]?.summary;
                                            summaryText = transSummary?.text || transSummary || (analysisResults.summary?.text || analysisResults.summary);
                                        }
                                    } else {
                                        // No translation, just show the summary
                                        summaryText = analysisResults.summary?.text || analysisResults.summary;
                                    }

                                    return (
                                        <>
                                            <p className="text-gray-300 leading-relaxed text-lg mb-4">
                                                {summaryText}
                                            </p>
                                            {analysisResults.summary?.sentences && (
                                                <div className="text-sm text-gray-500">
                                                    Condensed to {analysisResults.summary.sentences} key sentences
                                                </div>
                                            )}
                                        </>
                                    );
                                })()}
                            </motion.div>
                        )}

                        {/* Keywords */}
                        {(() => {
                            const translatedObj = analysisResults.analysis_translated || analysisResults.translated;
                            const targetLang = translatedObj ? Object.keys(translatedObj)[0] : null;
                            const keywords = (!showEnglish && translatedObj && targetLang)
                                ? (translatedObj[targetLang]?.keywords || analysisResults.keywords)
                                : analysisResults.keywords;

                            if (!keywords || keywords.length === 0) return null;

                            return (
                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: 0.2 }}
                                    className="p-8 bg-gradient-to-br from-amber-900/20 to-orange-900/20 rounded-3xl border border-amber-500/20 backdrop-blur-md"
                                >
                                    <h4 className="text-2xl font-black text-white mb-6">🔑 Key Topics</h4>
                                    <div className="flex flex-wrap gap-3">
                                        {keywords.slice(0, 10).map((keyword, index) => (
                                            <span
                                                key={index}
                                                className="px-4 py-2 bg-white/5 rounded-xl text-sm font-bold text-gray-300 border border-white/10 hover:bg-white/10 hover:text-white transition-colors shadow-sm"
                                            >
                                                {keyword}
                                            </span>
                                        ))}
                                    </div>
                                </motion.div>
                            );
                        })()}

                        {/* Entities */}
                        {(() => {
                            const translatedObj = analysisResults.analysis_translated || analysisResults.translated;
                            const targetLang = translatedObj ? Object.keys(translatedObj)[0] : null;
                            const entities = (!showEnglish && translatedObj && targetLang)
                                ? (translatedObj[targetLang]?.entities || analysisResults.entities)
                                : analysisResults.entities;

                            if (!entities || entities.length === 0) return null;

                            // Group entities by type
                            const entityGroups = entities.reduce((groups, entity) => {
                                const label = entity.label;
                                if (!groups[label]) groups[label] = [];
                                groups[label].push(entity.text);
                                return groups;
                            }, {});

                            const labelIcons = {
                                'PERSON': '👤',
                                'GPE': '🌍',
                                'ORG': '🏢',
                                'DATE': '📅',
                                'CARDINAL': '🔢',
                                'NORP': '👥',
                                'FAC': '🏛️',
                                'LOC': '📍',
                                'EVENT': '🎯'
                            };

                            return (
                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: 0.3 }}
                                    className="p-8 bg-gradient-to-br from-emerald-900/20 to-teal-900/20 rounded-3xl border border-emerald-500/20 backdrop-blur-md"
                                >
                                    <h4 className="text-2xl font-black text-white mb-6">👥 Named Entities</h4>
                                    <div className="grid md:grid-cols-2 gap-6">
                                        {Object.entries(entityGroups).slice(0, 8).map(([label, entities]) => {
                                            const uniqueEntities = [...new Set(entities)];
                                            const isExpanded = expandedGroups[label];
                                            const displayEntities = isExpanded ? uniqueEntities : uniqueEntities.slice(0, 5);
                                            const hasMore = uniqueEntities.length > 5;

                                            return (
                                                <div
                                                    key={label}
                                                    className={`bg-white/5 rounded-2xl p-4 border transition-all ${isExpanded ? 'border-emerald-500/50 shadow-[0_0_15px_rgba(16,185,129,0.1)]' : 'border-white/5'
                                                        }`}
                                                >
                                                    <div
                                                        className="flex items-center gap-2 mb-3 cursor-pointer group"
                                                        onClick={() => setExpandedGroups(prev => ({ ...prev, [label]: !prev[label] }))}
                                                    >
                                                        <span className="text-2xl">{labelIcons[label] || '📌'}</span>
                                                        <h5 className="font-black text-gray-200 group-hover:text-emerald-400 transition-colors">{label}</h5>
                                                        <span className="ml-auto text-xs font-bold text-gray-400 bg-white/5 px-2 py-1 rounded-lg">
                                                            {uniqueEntities.length}
                                                        </span>
                                                    </div>
                                                    <div className="flex flex-wrap gap-2">
                                                        {displayEntities.map((entity, idx) => (
                                                            <span
                                                                key={idx}
                                                                className="px-3 py-1 bg-emerald-500/10 rounded-lg text-xs font-bold text-gray-300 border border-emerald-500/20 hover:bg-emerald-500/20 transition-colors cursor-default"
                                                            >
                                                                {entity}
                                                            </span>
                                                        ))}
                                                        {hasMore && (
                                                            <button
                                                                onClick={() => setExpandedGroups(prev => ({ ...prev, [label]: !prev[label] }))}
                                                                className={`px-3 py-1 text-xs font-black rounded-lg transition-all ${isExpanded
                                                                        ? 'bg-emerald-600 text-white hover:bg-emerald-500'
                                                                        : 'text-emerald-400 hover:bg-emerald-500/10'
                                                                    }`}
                                                            >
                                                                {isExpanded ? 'Show Less' : `+${uniqueEntities.length - 5} more`}
                                                            </button>
                                                        )}
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </motion.div>
                            );
                        })()}

                        {/* Event Classification */}
                        {analysisResults.event && (
                            <motion.div
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.4 }}
                                className="p-8 bg-gradient-to-br from-rose-900/20 to-red-900/20 rounded-3xl border border-rose-500/20 backdrop-blur-md"
                            >
                                <h4 className="text-2xl font-black text-white mb-6">🎯 Event Classification</h4>
                                <div className="grid md:grid-cols-2 gap-6">
                                    <div className="bg-white/5 rounded-2xl p-6 border border-white/10">
                                        <div className="text-sm font-bold text-gray-400 mb-2">Event Type</div>
                                        <div className="text-2xl font-black text-white capitalize">
                                            {analysisResults.event.type}
                                        </div>
                                    </div>
                                    <div className="bg-white/5 rounded-2xl p-6 border border-white/10">
                                        <div className="text-sm font-bold text-gray-400 mb-2">Confidence</div>
                                        <div className="text-2xl font-black text-white">
                                            {(analysisResults.event.confidence * 100).toFixed(1)}%
                                        </div>
                                    </div>
                                </div>
                            </motion.div>
                        )}

                        {/* Location */}
                        {(() => {
                            const translatedObj = analysisResults.analysis_translated || analysisResults.translated;
                            const targetLang = translatedObj ? Object.keys(translatedObj)[0] : null;
                            const location = (!showEnglish && translatedObj && targetLang)
                                ? (translatedObj[targetLang]?.location || analysisResults.location)
                                : analysisResults.location;

                            if (!location || location.status === 'not_detected') return null;

                            return (
                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: 0.5 }}
                                    className="p-8 bg-gradient-to-br from-indigo-900/20 to-violet-900/20 rounded-3xl border border-indigo-500/20 backdrop-blur-md"
                                >
                                    <h4 className="text-2xl font-black text-white mb-6">📍 Location Analysis</h4>
                                    <div className="grid md:grid-cols-3 gap-6">
                                        <div className="bg-white/5 rounded-2xl p-6 border border-white/10 shadow-sm">
                                            <div className="text-sm font-bold text-gray-400 mb-2">Country</div>
                                            <div className="text-xl font-black text-white">
                                                {location.country}
                                            </div>
                                        </div>
                                        <div className="bg-white/5 rounded-2xl p-6 border border-white/10 shadow-sm">
                                            <div className="text-sm font-bold text-gray-400 mb-2">City</div>
                                            <div className="text-xl font-black text-white">
                                                {location.city}
                                            </div>
                                        </div>
                                        <div className="bg-white/5 rounded-2xl p-6 border border-white/10 shadow-sm">
                                            <div className="text-sm font-bold text-gray-400 mb-2">Confidence</div>
                                            <div className="text-xl font-black text-white">
                                                {(location.confidence * 100).toFixed(1)}%
                                            </div>
                                        </div>
                                    </div>
                                </motion.div>
                            );
                        })()}
                    </div>
                )}

                {/* Error State */}
                {error && (
                    <div className="mb-12 p-8 bg-red-500/10 rounded-3xl border border-red-500/20 flex items-start gap-4">
                        <AlertCircle size={32} className="text-red-400 flex-shrink-0" />
                        <div className="flex-1">
                            <h4 className="font-black text-red-400 text-xl mb-3">Analysis Failed</h4>
                            <p className="text-red-300 mb-6">{error}</p>
                            <button
                                onClick={startAnalysis}
                                className="px-6 py-3 bg-red-600 text-white rounded-xl font-bold hover:bg-red-500 transition-all"
                            >
                                Try Again
                            </button>
                        </div>
                    </div>
                )}

                {/* Read Original Article */}
                <div className="pt-8 border-t border-white/10">
                    <a
                        href={article.original_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-3 px-8 py-4 bg-white/5 text-gray-300 rounded-2xl font-bold hover:bg-white/10 hover:text-white transition-all border border-white/10"
                    >
                        <ExternalLink size={20} />
                        Read Original Article
                    </a>
                </div>
            </div>
        </div>
    );
}
