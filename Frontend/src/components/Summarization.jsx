import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { FileText, Sparkles, ChevronDown, Clock, Layers, Loader2, AlertCircle, Zap } from 'lucide-react';
import { AnimatePresence } from 'framer-motion';
import { api } from '../services/api';

export default function Summarization() {
    const [documents, setDocuments] = useState([]);
    const [selectedDocId, setSelectedDocId] = useState('');
    const [pastedText, setPastedText] = useState('');
    const [activeTab, setActiveTab] = useState('document');
    const [summaryData, setSummaryData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
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

    const handleGenerateSummary = async () => {
        const idToSummarize = activeTab === 'document' ? selectedDocId : null;

        if (activeTab === 'document' && !selectedDocId) return;
        if (activeTab === 'paste' && !pastedText.trim()) return;

        setLoading(true);
        setError(null);
        setSummaryData(null);

        try {
            let finalDocId = selectedDocId;

            if (activeTab === 'paste') {
                const uploadRes = await api.uploadDocument(new File([pastedText], 'pasted.txt', { type: 'text/plain' }));
                if (uploadRes.status !== 'success') throw new Error("Text upload failed");
                finalDocId = uploadRes.data.document_id;
            }

            const response = await api.generateSummary(finalDocId);
            if (response.status === 'success' && response.data?.success !== false) {
                setSummaryData(response.data);
            } else {
                const reason = response.data?.reason || response.message || "Summarization failed";
                setError(`Summarization failed: ${reason}`);
            }
        } catch (err) {
            console.error("Summarization failed:", err);
            setError(err.message || "Summarization failed");
        } finally {
            setLoading(false);
            setDisplayMode('english');
        }
    };

    return (
        <div className="space-y-8 animate-fade-in max-w-6xl mx-auto mb-20">
            <div>
                <h2 className="text-3xl font-black text-white mb-2 tracking-tight">Document Summary</h2>
                <p className="text-gray-400 font-medium">Generate AI-powered summaries of your documents instantly.</p>
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
                        <Sparkles size={20} />
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
                                            <p className="text-[10px] text-gray-500">Choose a document to summarize</p>
                                        </div>
                                    </div>

                                    <div className="relative">
                                        <select
                                            value={selectedDocId}
                                            onChange={(e) => {
                                                setSelectedDocId(e.target.value);
                                                setSummaryData(null);
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
                                        onClick={handleGenerateSummary}
                                        disabled={loading || !selectedDocId || documents.length === 0}
                                        className="bg-indigo-600 text-white px-10 py-4 rounded-2xl font-black text-lg flex items-center justify-center gap-3 shadow-xl shadow-indigo-500/20 hover:brightness-110 active:scale-95 transition-all w-full md:w-auto disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {loading ? <Loader2 className="animate-spin" size={20} /> : <Sparkles size={20} />}
                                        {loading ? 'Generating...' : 'Generate Summary'}
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
                                            <Sparkles size={20} />
                                        </div>
                                        <div>
                                            <h3 className="font-bold text-white uppercase tracking-wider text-xs">Paste Content</h3>
                                            <p className="text-[10px] text-gray-500">Summarize direct text input</p>
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
                                        onClick={handleGenerateSummary}
                                        disabled={loading || !pastedText.trim()}
                                        className="bg-indigo-600 text-white px-10 py-4 rounded-2xl font-black text-lg flex items-center justify-center gap-3 shadow-xl shadow-indigo-500/20 hover:brightness-110 active:scale-95 transition-all w-full md:w-auto disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {loading ? <Loader2 className="animate-spin" size={20} /> : <Sparkles size={20} />}
                                        {loading ? 'Generating...' : 'Generate Summary'}
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

                {summaryData && (
                    <div className="animate-fade-in space-y-8 p-10">
                        <div className="space-y-6">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 bg-indigo-500/10 rounded-xl flex items-center justify-center text-indigo-400 border border-indigo-500/20">
                                    <FileText size={20} />
                                </div>
                                <h3 className="font-black text-white text-xl tracking-tight">Analysis Result</h3>
                            </div>

                             {/* Language Toggle */}
                             {summaryData.language && summaryData.language !== 'en' && (
                                <div className="bg-white/5 p-1 rounded-xl border border-white/10 flex items-center">
                                    <button
                                        onClick={() => setDisplayMode('native')}
                                        className={`px-4 py-2 rounded-lg text-xs font-black uppercase tracking-widest transition-all ${displayMode === 'native' ? 'bg-indigo-600 text-white shadow-lg' : 'text-gray-500 hover:text-white'}`}
                                    >
                                        Native ({summaryData.language})
                                    </button>
                                    <button
                                        onClick={() => setDisplayMode('english')}
                                        className={`px-4 py-2 rounded-lg text-xs font-black uppercase tracking-widest transition-all ${displayMode === 'english' ? 'bg-indigo-600 text-white shadow-lg' : 'text-gray-500 hover:text-white'}`}
                                    >
                                        English
                                    </button>
                                </div>
                            )}


                            {/* Summary Text (Dynamic) */}
                            <div className="space-y-3">
                                <div className="flex items-center gap-2">
                                    <span className="text-xs font-black text-gray-500 uppercase tracking-widest">
                                        {displayMode === 'english' ? 'English Summary' : `Native Summary (${summaryData.language})`}
                                    </span>
                                </div>
                                <div className="p-12 bg-white/5 border border-white/10 rounded-[32px] text-white leading-loose font-medium text-lg shadow-inner">
                                    {displayMode === 'english'
                                        ? (() => {
                                            const enSum = summaryData?.summary?.en;
                                            if (typeof summaryData?.summary === 'string') return summaryData.summary;
                                            if (typeof enSum === 'string') return enSum;
                                            if (typeof enSum === 'object' && enSum?.en) return enSum.en;
                                            return "No summary available";
                                        })()
                                        : (summaryData?.summary?.native?.text || summaryData?.summary?.native || "No native summary available")
                                    }
                                </div>
                            </div>
                        </div>

                        <div className="grid md:grid-cols-2 gap-6">
                            <div className="p-6 rounded-[24px] bg-indigo-500/10 border border-indigo-500/20 shadow-sm relative overflow-hidden group">
                                <p className="text-[10px] font-black text-indigo-400 uppercase tracking-widest mb-3">Reduction</p>
                                <p className="text-4xl font-black text-indigo-400 tracking-tight">
                                    {summaryData?.stats?.reduction_percentage ?? 0}%
                                </p>
                                <Sparkles className="absolute bottom-[-10%] right-[-10%] w-24 h-24 text-indigo-400/20 opacity-100 rotate-12 group-hover:scale-110 transition-transform duration-500" />
                            </div>

                            <div className="p-6 rounded-[24px] bg-blue-500/10 border border-blue-500/20 shadow-sm relative overflow-hidden group">
                                <p className="text-[10px] font-black text-blue-400 uppercase tracking-widest mb-3">Time Taken</p>
                                <p className="text-4xl font-black text-blue-400 tracking-tight">
                                    {summaryData?.stats?.time_taken ?? 0}s
                                </p>
                                <Clock className="absolute bottom-[-10%] right-[-10%] w-24 h-24 text-blue-400/20 opacity-100 rotate-12 group-hover:scale-110 transition-transform duration-500" />
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
