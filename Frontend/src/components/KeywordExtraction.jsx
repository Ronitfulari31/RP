import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Target, ChevronDown, Activity, Zap, Loader2, AlertCircle, Globe, FileText } from 'lucide-react';
import { api } from '../services/api';

export default function KeywordExtraction() {
    const [documents, setDocuments] = useState([]);
    const [selectedDocId, setSelectedDocId] = useState('');
    const [pastedText, setPastedText] = useState('');
    const [activeTab, setActiveTab] = useState('document');
    const [keywordData, setKeywordData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [selectedLanguage, setSelectedLanguage] = useState('en');
    const [displayMode, setDisplayMode] = useState('english'); // 'english' | 'native'
    const hasFetched = useRef(false);

    useEffect(() => {
        if (!hasFetched.current) {
            fetchDocuments();
            hasFetched.current = true;
        }
    }, []);

    const fetchDocuments = async () => {
        try {
            const response = await api.listDocuments();
            if (response.status === 'success' && response.data.documents?.length > 0) {
                setDocuments(response.data.documents);
                setSelectedDocId(response.data.documents[0].document_id);
            } else {
                setDocuments([]);
            }
        } catch (err) {
            console.error("Failed to fetch documents:", err);
            setDocuments([]);
            setError("Could not load documents");
        }
    };

    const handleExtractKeywords = async () => {
        if (activeTab === 'document' && !selectedDocId) return;
        if (activeTab === 'paste' && !pastedText.trim()) return;

        setLoading(true);
        setKeywordData(null);
        setError(null);

        try {
            let finalDocId = selectedDocId;

            if (activeTab === 'paste') {
                const uploadRes = await api.uploadDocument(new File([pastedText], 'pasted.txt', { type: 'text/plain' }));
                if (uploadRes.status !== 'success') throw new Error("Text upload failed");
                finalDocId = uploadRes.data.document_id;
            }

            const response = await api.extractKeywords(finalDocId);
            if (response.status === 'success' && response.data?.success !== false) {
                setKeywordData(response.data);
                setSelectedLanguage('en');
            } else {
                const reason = response.data?.reason || response.message || "Keyword extraction failed";
                setError(`Keyword extraction failed: ${reason}`);
            }
        } catch (err) {
            console.error("Keyword extraction failed:", err);
            setError(err.message || "Keyword extraction failed");
        } finally {
            setLoading(false);
        }
    };

    // Helper to assign colors based on rank
    const getKeywordColor = (rank) => {
        if (rank <= 3) return 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30';
        if (rank <= 7) return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
        if (rank <= 10) return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
        return 'bg-white/5 text-gray-400 border-white/10';
    };

    const getKeywordSize = (rank) => {
        if (rank <= 3) return 'text-2xl';
        if (rank <= 7) return 'text-xl';
        return 'text-lg';
    };

    // Get available languages from keyword data
    const availableLanguages = (keywordData?.keywords && !Array.isArray(keywordData.keywords)) 
        ? Object.keys(keywordData.keywords) 
        : ['en'];
    
    // Determine keywords based on Display Mode
    const currentKeywords = Array.isArray(keywordData?.keywords)
        ? keywordData.keywords.map((kw, i) => ({ text: kw, score: 100 - i, rank: i + 1 })) 
        : (displayMode === 'english' 
            ? (keywordData?.keywords?.en || [])
            : (keywordData?.keywords?.native || [])
          ).map((kw, i) => ({ text: kw, score: 100 - i, rank: i + 1 }));

    return (
        <div className="space-y-8 animate-fade-in max-w-6xl mx-auto pb-12">
            <div>
                <h2 className="text-3xl font-black text-white mb-2 tracking-tight">Keyword Extraction</h2>
                <p className="text-gray-400 font-medium">Extract high-quality keywords using advanced RAKE algorithm.</p>
            </div>

            <div className="bg-[#0f172a]/40 backdrop-blur-xl rounded-[40px] border border-white/10 overflow-hidden shadow-2xl">
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
                        <Zap size={20} />
                        Paste Text
                    </button>
                </div>

                {/* Content */}
                <div className="p-10">
                    <AnimatePresence mode="wait">
                        {activeTab === 'document' ? (
                            <motion.div
                                key="document"
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: 10 }}
                                className="space-y-6"
                            >
                                <div className="space-y-4">
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 bg-indigo-500/10 rounded-xl flex items-center justify-center text-indigo-400 border border-indigo-500/20">
                                            <FileText size={20} />
                                        </div>
                                        <div>
                                            <h3 className="font-bold text-white uppercase tracking-wider text-xs">Select Document</h3>
                                            <p className="text-[10px] text-gray-500">Pick a document for keyword extraction</p>
                                        </div>
                                    </div>

                                    <div className="relative">
                                        <select
                                            value={selectedDocId}
                                            onChange={(e) => {
                                                setSelectedDocId(e.target.value);
                                                setKeywordData(null);
                                                setError(null);
                                            }}
                                            className="w-full p-4 bg-white/5 border border-white/10 rounded-xl appearance-none outline-none focus:ring-4 focus:ring-indigo-500/10 font-bold text-white cursor-pointer transition-all hover:bg-white/10"
                                        >
                                            <option value="" className="bg-[#0f172a]">-- Select a document --</option>
                                            {documents.map(doc => (
                                                <option key={doc.document_id} value={doc.document_id} className="bg-[#0f172a]">
                                                    {doc.filename}
                                                </option>
                                            ))}
                                        </select>
                                        <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" size={20} />
                                    </div>
                                </div>

                                <div className="flex justify-center pt-4">
                                    <button
                                        onClick={handleExtractKeywords}
                                        disabled={loading || (activeTab === 'document' && !selectedDocId) || documents.length === 0}
                                        className="bg-indigo-600 text-white px-10 py-4 rounded-2xl font-black text-lg flex items-center justify-center gap-3 shadow-xl shadow-indigo-500/20 hover:brightness-110 active:scale-95 transition-all w-full md:w-auto disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {loading ? <Loader2 className="animate-spin" size={20} /> : <Zap size={20} />}
                                        {loading ? 'Extracting...' : 'Extract Keywords'}
                                    </button>
                                </div>
                            </motion.div>
                        ) : (
                            <motion.div
                                key="paste"
                                initial={{ opacity: 0, x: 10 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -10 }}
                                className="space-y-6"
                            >
                                <div className="space-y-4">
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 bg-purple-500/10 rounded-xl flex items-center justify-center text-purple-400 border border-purple-500/20">
                                            <Zap size={20} />
                                        </div>
                                        <div>
                                            <h3 className="font-bold text-white uppercase tracking-wider text-xs">Analyze Text</h3>
                                            <p className="text-[10px] text-gray-500">Extract keywords from pasted text</p>
                                        </div>
                                    </div>

                                    <div className="relative">
                                        <textarea
                                            value={pastedText}
                                            onChange={(e) => setPastedText(e.target.value)}
                                            placeholder="Paste or type text here..."
                                            className="w-full h-48 p-6 bg-white/5 border border-white/10 rounded-2xl outline-none focus:ring-2 focus:ring-indigo-500/20 transition-all resize-none text-white placeholder:text-gray-600"
                                            disabled={loading}
                                        />
                                        <div className="absolute bottom-4 right-6 text-[10px] font-bold text-gray-500 uppercase tracking-widest">
                                            {pastedText.length} characters
                                        </div>
                                    </div>
                                </div>

                                <div className="flex justify-center pt-4">
                                    <button
                                        onClick={handleExtractKeywords}
                                        disabled={loading || !pastedText.trim()}
                                        className="bg-indigo-600 text-white px-10 py-4 rounded-2xl font-black text-lg flex items-center justify-center gap-3 shadow-xl shadow-indigo-500/20 hover:brightness-110 active:scale-95 transition-all w-full md:w-auto disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {loading ? <Loader2 className="animate-spin" size={20} /> : <Zap size={20} />}
                                        {loading ? 'Extracting...' : 'Extract Keywords'}
                                    </button>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {error && (
                        <div className="mt-6 p-4 bg-red-500/10 text-red-400 rounded-2xl flex items-center gap-3 font-bold text-sm animate-fade-in border border-red-500/20">
                            <AlertCircle size={18} />
                            {error}
                        </div>
                    )}
                </div>

                {keywordData && (
                    <div className="space-y-12 animate-fade-in">
                        {/* Standardized Language Toggle */}
                        {keywordData.language && keywordData.language !== 'en' && (
                            <div className="flex justify-center">
                                <div className="bg-white/5 p-1 rounded-xl border border-white/10 flex items-center inline-flex">
                                    <button
                                        onClick={() => setDisplayMode('native')}
                                        className={`px-6 py-2 rounded-lg text-sm font-black uppercase tracking-widest transition-all ${displayMode === 'native' ? 'bg-indigo-600 text-white shadow-lg' : 'text-gray-500 hover:text-white'}`}
                                    >
                                        Native ({keywordData.language})
                                    </button>
                                    <button
                                        onClick={() => setDisplayMode('english')}
                                        className={`px-6 py-2 rounded-lg text-sm font-black uppercase tracking-widest transition-all ${displayMode === 'english' ? 'bg-indigo-600 text-white shadow-lg' : 'text-gray-500 hover:text-white'}`}
                                    >
                                        English
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* Keyword Cloud */}
                        <div className="p-10 bg-white/5 border border-white/10 rounded-3xl">
                            <div className="flex items-center gap-3 mb-10">
                                <Activity className="text-indigo-400" size={20} />
                                <h3 className="font-black text-white text-lg">Keyword Insights</h3>
                                <span className="ml-auto text-xs font-bold text-gray-500">
                                    {keywordData.stats.total_keywords} keywords • {keywordData.stats.time_taken}s
                                </span>
                            </div>

                            <div className="flex flex-wrap justify-center gap-3 max-w-5xl mx-auto">
                                {currentKeywords.map((kw, i) => (
                                    <motion.div
                                        key={i}
                                        initial={{ scale: 0.8, opacity: 0 }}
                                        animate={{ scale: 1, opacity: 1 }}
                                        transition={{ delay: i * 0.05 }}
                                        className={`${getKeywordColor(kw.rank)} ${getKeywordSize(kw.rank)} px-8 py-4 rounded-full font-bold shadow-sm border transition-all cursor-default hover:scale-110`}
                                    >
                                        {kw.text}
                                    </motion.div>
                                ))}
                            </div>
                        </div>

                        {/* Relevance Scores */}
                        <div className="p-10 bg-white/5 border border-white/10 rounded-3xl">
                            <div className="flex items-center gap-3 mb-10">
                                <span className="text-indigo-400 font-bold text-xl">#</span>
                                <h3 className="font-black text-white text-lg">Keyword Relevance Scores</h3>
                            </div>

                            <div className="grid md:grid-cols-2 gap-x-12 gap-y-6">
                                {currentKeywords.map((keyword, i) => (
                                    <motion.div
                                        key={keyword.rank}
                                        initial={{ opacity: 0, x: -20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: i * 0.03 }}
                                        className="bg-white/5 p-5 rounded-2xl border border-white/10 flex items-center gap-6 group hover:bg-white/10 transition-all"
                                    >
                                        <div className="w-10 h-10 bg-indigo-500/10 rounded-lg flex items-center justify-center text-indigo-400 font-black text-sm">
                                            {keyword.rank}
                                        </div>
                                        <div className="flex-1 space-y-3">
                                            <div className="flex justify-between items-center px-1">
                                                <span className="font-bold text-gray-200">{keyword.text}</span>
                                                <span className="text-[10px] font-bold text-gray-500 tabular-nums">{keyword.score}%</span>
                                            </div>
                                            <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                                                <motion.div
                                                    initial={{ width: 0 }}
                                                    animate={{ width: `${keyword.score}%` }}
                                                    transition={{ duration: 1, delay: 0.5 + i * 0.05 }}
                                                    className="h-full bg-indigo-500 rounded-full"
                                                />
                                            </div>
                                        </div>
                                    </motion.div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
