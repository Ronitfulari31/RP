import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Globe,
    ArrowRight,
    Languages,
    CheckCircle2,
    ArrowLeftRight,
    Copy,
    Check,
    RotateCcw,
    Zap,
    AlertCircle,
    Loader2,
    FileText,
    ChevronDown,
    Sparkles
} from 'lucide-react';
import { api } from '../services/api';

const LANGUAGES = [
    { code: 'en', name: 'English' },
    { code: 'ar', name: 'Arabic' },
    { code: 'fr', name: 'French' },
    { code: 'hi', name: 'Hindi' },
    { code: 'es', name: 'Spanish' },
    { code: 'nl', name: 'Dutch' },
    { code: 'id', name: 'Indonesian' },
    { code: 'sw', name: 'Swahili' },
    { code: 'zh', name: 'Chinese (Simplified)' }
];

export default function Translation() {
    const [sourceLang, setSourceLang] = useState('');
    const [targetLang, setTargetLang] = useState('');
    const [sourceText, setSourceText] = useState('');
    const [translatedText, setTranslatedText] = useState('');
    const [isCopied, setIsCopied] = useState(false);
    const [isTranslating, setIsTranslating] = useState(false);
    const [isFetchingDoc, setIsFetchingDoc] = useState(false);
    const [error, setError] = useState('');
    const [stats, setStats] = useState(null);

    // Document loading state
    const [activeTab, setActiveTab] = useState('paste');
    const [documents, setDocuments] = useState([]);
    const [selectedDocId, setSelectedDocId] = useState('');
    const [isLoadingDocs, setIsLoadingDocs] = useState(false);
    const hasFetched = useRef(false);

    useEffect(() => {
        if (!hasFetched.current) {
            fetchDocuments();
            hasFetched.current = true;
        }
    }, []);

    const fetchDocuments = async () => {
        setIsLoadingDocs(true);
        try {
            const response = await api.listDocuments();
            if (response.status === 'success' && response.data.documents?.length > 0) {
                setDocuments(response.data.documents);
            } else {
                setDocuments([]);
            }
        } catch (err) {
            console.error("Failed to fetch documents:", err);
            setDocuments([]);
        } finally {
            setIsLoadingDocs(false);
        }
    };

    const handleDocumentSelect = async (docId) => {
        setSelectedDocId(docId);
        if (!docId) return;

        setIsFetchingDoc(true); // Separate from isTranslating
        setError('');
        try {
            const response = await api.getDocument(docId);
            if (response.status === 'success' && response.data.raw_text) {
                const text = response.data.raw_text;
                setSourceText(text);
                setTranslatedText('');
                setStats(null);
                setActiveTab('paste'); // Auto-switch to editor view
                setSelectedDocId(''); // Reset selection after import

                // Auto-detect language
                let detectedLang = response.data.language;

                if (!detectedLang || detectedLang === 'unknown') {
                    try {
                        const detectRes = await api.detectLanguage(text);
                        if (detectRes.status === 'success') {
                            detectedLang = detectRes.data.language;
                        }
                    } catch (detectErr) {
                        console.warn('Auto-detection failed:', detectErr);
                    }
                }

                // Apply detected language
                if (detectedLang && detectedLang !== 'unknown') {
                    // Check if supported
                    const isSupported = LANGUAGES.some(l => l.code === detectedLang);
                    if (isSupported) {
                        setSourceLang(detectedLang);

                        // Auto-set target to English if source is not English, else Spanish (or keep existing)
                        if (detectedLang !== 'en') {
                            setTargetLang('en');
                        } else if (targetLang === 'en') {
                            setTargetLang('es'); // Default to Spanish if source is English
                        }
                    }
                }
            }
        } catch (err) {
            console.error("Failed to load document content:", err);
            setError("Failed to load document content");
        } finally {
            setIsFetchingDoc(false);
        }
    };

    const handleSwap = () => {
        if (!sourceLang || !targetLang) return; // Only swap if both are selected
        setSourceLang(targetLang);
        setTargetLang(sourceLang);
        setSourceText(translatedText);
        setTranslatedText(sourceText);
        setStats(null);
    };

    const handleCopy = () => {
        if (!translatedText) return;
        navigator.clipboard.writeText(translatedText);
        setIsCopied(true);
        setTimeout(() => setIsCopied(false), 2000);
    };

    const handleTranslate = async () => {
        if (!sourceText.trim()) return;

        if (!sourceLang || !targetLang) {
            setError("Please select both source and target languages first.");
            return;
        }

        setIsTranslating(true);
        setError('');
        setStats(null);

        try {
            const response = await api.translate(sourceText, sourceLang, targetLang);
            if (response.status === 'success') {
                setTranslatedText(response.data.translated_text);
                setStats(response.data.stats || null);
            }
        } catch (err) {
            setError(err.message || 'Translation failed');
        } finally {
            setIsTranslating(false);
        }
    };

    return (
        <div className="space-y-10 animate-fade-in max-w-6xl mx-auto mb-20">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                <div>
                    <h2 className="text-4xl font-black text-white tracking-tight mb-3">Multi-Language Bridge</h2>
                    <p className="text-gray-400 text-lg font-medium">Neural machine translation with enterprise-grade linguistic precision.</p>
                </div>
            </div>

            <div className="bg-[#0f172a]/40 backdrop-blur-xl rounded-[48px] border border-white/10 shadow-2xl shadow-indigo-500/5 relative overflow-hidden">
                {/* Tabs */}
                <div className="flex border-b border-white/5 bg-white/5">
                    <button
                        onClick={() => setActiveTab('document')}
                        className={`flex-1 py-4 px-6 flex items-center justify-center gap-2 font-semibold transition-all ${activeTab === 'document'
                            ? 'bg-white/5 text-indigo-400 border-b-2 border-indigo-500 shadow-[inset_0_-2px_0_0_#6366f1]'
                            : 'text-gray-400 hover:text-white hover:bg-white/5'
                            }`}
                    >
                        <FileText size={20} />
                        Choose Document
                    </button>
                    <button
                        onClick={() => setActiveTab('paste')}
                        className={`flex-1 py-4 px-6 flex items-center justify-center gap-2 font-semibold transition-all ${activeTab === 'paste'
                            ? 'bg-white/5 text-indigo-400 border-b-2 border-indigo-500 shadow-[inset_0_-2px_0_0_#6366f1]'
                            : 'text-gray-400 hover:text-white hover:bg-white/5'
                            }`}
                    >
                        <Sparkles size={20} />
                        Paste Text
                    </button>
                </div>

                {/* Header Controls */}
                <div className="p-8 border-b border-white/5 bg-white/5">
                    <div className="flex flex-col gap-6">
                        {/* Tab Content: Document Selector */}
                        <AnimatePresence mode="wait">
                            {activeTab === 'document' && (
                                <motion.div
                                    key="doc-select"
                                    initial={{ opacity: 0, y: -10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -10 }}
                                    className="space-y-2"
                                >
                                    <label className="block text-[10px] font-black text-gray-500 uppercase tracking-widest mb-2 ml-1">Select Document to Translate</label>
                                    <div className="relative">
                                        <select
                                            value={selectedDocId}
                                            onChange={(e) => handleDocumentSelect(e.target.value)}
                                            className="w-full p-4 bg-white/5 border border-white/10 rounded-xl outline-none focus:ring-4 focus:ring-indigo-500/10 font-bold text-white shadow-sm transition-all appearance-none cursor-pointer"
                                            disabled={isLoadingDocs || isFetchingDoc}
                                        >
                                            <option value="" className="bg-[#0f172a]">-- Select a document --</option>
                                            {documents.map(doc => (
                                                <option key={doc.document_id} value={doc.document_id} className="bg-[#0f172a]">
                                                    {doc.filename}
                                                </option>
                                            ))}
                                        </select>
                                        {isFetchingDoc ? (
                                            <Loader2 size={20} className="absolute right-4 top-1/2 -translate-y-1/2 text-indigo-400 animate-spin" />
                                        ) : (
                                            <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" size={20} />
                                        )}
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                            <div className="w-full md:w-auto flex items-center gap-4">
                                <div className="flex-1 md:w-64">
                                    <label className="block text-[10px] font-black text-gray-500 uppercase tracking-widest mb-2 ml-1">Source Language</label>
                                    <div className="relative">
                                        <select
                                            value={sourceLang}
                                            onChange={(e) => {
                                                const newSource = e.target.value;
                                                setSourceLang(newSource);
                                                setTranslatedText('');
                                                setStats(null);

                                                // Auto-switch target if same as new source
                                                if (newSource === targetLang) {
                                                    const newTarget = LANGUAGES.find(l => l.code !== newSource)?.code;
                                                    if (newTarget) setTargetLang(newTarget);
                                                }
                                            }}
                                            className="w-full p-4 bg-white/5 border border-white/10 rounded-xl outline-none focus:ring-4 focus:ring-indigo-500/10 font-bold text-white shadow-sm transition-all appearance-none cursor-pointer"
                                        >
                                            <option value="" disabled className="bg-[#0f172a]">Choose Language</option>
                                            {LANGUAGES.map(lang => (
                                                <option key={lang.code} value={lang.code} className="bg-[#0f172a]">{lang.name}</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>

                                <button
                                    onClick={handleSwap}
                                    className="mt-6 w-12 h-12 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-indigo-400 shadow-sm hover:shadow-md hover:scale-105 active:scale-95 transition-all hover:bg-white/10"
                                    title="Swap Languages"
                                >
                                    <ArrowLeftRight size={20} />
                                </button>

                                <div className="flex-1 md:w-64">
                                    <label className="block text-[10px] font-black text-gray-500 uppercase tracking-widest mb-2 ml-1">Target Language</label>
                                    <select
                                        value={targetLang}
                                        onChange={(e) => setTargetLang(e.target.value)}
                                        className="w-full p-4 bg-white/5 border border-white/10 rounded-xl outline-none focus:ring-4 focus:ring-indigo-500/10 font-bold text-white shadow-sm transition-all appearance-none cursor-pointer"
                                    >
                                        <option value="" disabled className="bg-[#0f172a]">Choose Language</option>
                                        {LANGUAGES
                                            .filter(lang => lang.code !== sourceLang)
                                            .map(lang => (
                                                <option key={lang.code} value={lang.code} className="bg-[#0f172a]">{lang.name}</option>
                                            ))}
                                    </select>
                                </div>
                            </div>

                            <div className="flex items-center gap-4 w-full md:w-auto">
                                <button
                                    onClick={handleTranslate}
                                    disabled={isTranslating || !sourceText.trim()}
                                    className="flex-1 md:flex-none bg-indigo-600 text-white px-10 py-4 rounded-2xl font-black text-lg shadow-xl shadow-indigo-500/20 hover:brightness-110 active:scale-95 transition-all flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {isTranslating ? (
                                        <RotateCcw className="animate-spin" size={20} />
                                    ) : (
                                        <Languages size={22} />
                                    )}
                                    Translate
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Text Areas */}
                <div className="grid lg:grid-cols-2">
                    {/* Source Text Area */}
                    <div className="p-8 border-b lg:border-b-0 lg:border-r border-white/5 flex flex-col h-full bg-[#0f172a]/20">
                        <div className="flex items-center justify-between mb-4">
                            <span className="flex items-center gap-2 text-xs font-black text-gray-500 uppercase tracking-widest bg-white/5 px-3 py-1.5 rounded-lg border border-white/10">
                                <Globe size={14} className="text-indigo-400" />
                                Input: {LANGUAGES.find(l => l.code === sourceLang)?.name || 'Language'}
                            </span>
                            <span className="text-[10px] font-bold text-gray-600">
                                {sourceText.length} characters
                            </span>
                        </div>
                        <textarea
                            value={sourceText}
                            onChange={(e) => setSourceText(e.target.value)}
                            placeholder="Type something to translate..."
                            className="w-full flex-grow min-h-[300px] p-0 bg-transparent outline-none text-xl font-semibold text-white leading-relaxed resize-none placeholder:text-gray-700"
                        />
                        {error && (
                            <div className="mt-4 p-3 bg-red-500/10 text-red-400 rounded-xl flex items-center gap-2 text-sm font-bold animate-fade-in border border-red-500/20">
                                <AlertCircle size={16} />
                                {error}
                            </div>
                        )}
                    </div>

                    {/* Target Text Area */}
                    <div className="p-8 bg-[#0f172a]/40 flex flex-col h-full relative">
                        {isTranslating && (
                            <div className="absolute inset-0 bg-[#0f172a]/60 backdrop-blur-[2px] z-10 flex items-center justify-center">
                                <div className="bg-[#0f172a] p-4 rounded-2xl shadow-xl flex items-center gap-3 animate-bounce-subtle border border-white/10">
                                    <Loader2 size={24} className="animate-spin text-indigo-400" />
                                    <span className="font-bold text-white">Translating...</span>
                                </div>
                            </div>
                        )}
                        <div className="flex items-center justify-between mb-4">
                            <span className="flex items-center gap-2 text-xs font-black text-emerald-400 uppercase tracking-widest bg-emerald-500/10 px-3 py-1.5 rounded-lg border border-emerald-500/20">
                                <CheckCircle2 size={14} className="text-emerald-400" />
                                Output: {LANGUAGES.find(l => l.code === targetLang)?.name || 'Language'}
                            </span>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={handleCopy}
                                    disabled={!translatedText}
                                    className={`p-2 rounded-xl border transition-all flex items-center gap-2 font-bold text-xs ${isCopied ? 'bg-emerald-600 text-white border-emerald-500 shadow-lg shadow-emerald-500/20' : 'bg-white/5 border-white/10 text-gray-500 hover:bg-white/10 hover:text-white disabled:opacity-50'}`}
                                >
                                    {isCopied ? <Check size={14} /> : <Copy size={14} />}
                                    {isCopied ? 'Copied!' : 'Copy'}
                                </button>
                            </div>
                        </div>
                        <div className={`w-full flex-grow min-h-[300px] text-xl font-semibold leading-relaxed transition-all duration-500 ${!translatedText ? 'text-gray-700 italic' : 'text-white'}`}>
                            {translatedText || 'Translation will appear here...'}
                        </div>

                        {/* Accuracy Footer */}
                        {stats && (
                            <div className="mt-8 pt-6 border-t border-white/5 flex items-center justify-between animate-fade-in">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 bg-indigo-500/10 rounded-xl flex items-center justify-center text-indigo-400 border border-indigo-500/20">
                                        <CheckCircle2 size={20} />
                                    </div>
                                    <div>
                                        <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest leading-none mb-1">Confidence Score</p>
                                        <p className="text-lg font-black text-emerald-400 leading-none">{(stats.confidence * 100).toFixed(1)}%</p>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest leading-none mb-1">Latency</p>
                                    <p className="text-lg font-black text-white leading-none">{stats.latency}</p>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
