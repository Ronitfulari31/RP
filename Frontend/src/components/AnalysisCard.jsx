import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CloudUpload, FileText, Upload, Sparkles, Loader2, FileCheck, AlertCircle, X, Type, Edit3, ChevronDown } from 'lucide-react';
import { api } from '../services/api';

export default function AnalysisCard({ onNavigate }) {
    const [activeTab, setActiveTab] = useState('upload');
    const [isUploading, setIsUploading] = useState(false);
    const [text, setText] = useState('');
    const [selectedFiles, setSelectedFiles] = useState([]);
    const [isDragging, setIsDragging] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [saveAsFileName, setSaveAsFileName] = useState('');
    const [saveAsFormat, setSaveAsFormat] = useState('txt');
    const fileInputRef = useRef(null);

    const handleFileChange = (e) => {
        if (e.target.files && e.target.files.length > 0) {
            const newFiles = Array.from(e.target.files).map(f => ({
                id: Math.random().toString(36).substring(2, 9) + Date.now(),
                file: f
            }));
            setSelectedFiles(prev => [...prev, ...newFiles]);
            setError('');
            // Reset input value to allow the same file to be selected again
            e.target.value = '';
        }
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = (e) => {
        e.preventDefault();
        if (e.currentTarget.contains(e.relatedTarget)) return;
        setIsDragging(false);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setIsDragging(false);
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            const newFiles = Array.from(e.dataTransfer.files).map(f => ({
                id: Math.random().toString(36).substring(2, 9) + Date.now(),
                file: f
            }));
            setSelectedFiles(prev => [...prev, ...newFiles]);
            setError('');
        }
    };

    const removeFile = (idToRemove) => {
        setSelectedFiles(prev => prev.filter(item => item.id !== idToRemove));
        setError('');
        setSuccess('');
    };


    const handleAnalyze = async () => {
        setIsUploading(true);
        setError('');
        setSuccess('');

        try {
            if (activeTab === 'upload') {
                if (selectedFiles.length === 0) throw new Error('Please select at least one file');

                let successCount = 0;
                for (const item of selectedFiles) {
                    await api.uploadDocument(item.file);
                    successCount++;
                }
                setSuccess(`Successfully uploaded ${successCount} document${successCount !== 1 ? 's' : ''}!`);
            } else {
                if (!text.trim()) throw new Error('Please paste some text first');

                // Create a virtual file to upload so it has a name and extension
                const fileName = saveAsFileName.trim() || 'pasted-document';
                const file = new File([text], `${fileName}.${saveAsFormat}`, {
                    type: saveAsFormat === 'txt' ? 'text/plain' :
                        saveAsFormat === 'pdf' ? 'application/pdf' :
                            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                });

                await api.uploadDocument(file);
                setSuccess(`Document saved as ${fileName}.${saveAsFormat} successfully!`);
            }

            // Redirect to Document List after short delay
            if (onNavigate) {
                setTimeout(() => onNavigate('documents'), 1500);
            }
        } catch (err) {
            setError(err.message || 'Upload failed. Please try again.');
        } finally {
            setIsUploading(false);
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="max-w-4xl mx-auto mb-20"
        >
            <div className="bg-[#0f172a]/40 backdrop-blur-xl rounded-[40px] border border-white/10 overflow-hidden shadow-2xl">
                {/* Tabs */}
                <div className="flex border-b border-white/5 bg-white/5">
                    <button
                        onClick={() => setActiveTab('upload')}
                        className={`flex-1 py-4 px-6 flex items-center justify-center gap-2 font-semibold transition-all ${activeTab === 'upload'
                            ? 'bg-white/5 text-indigo-400 border-b-2 border-indigo-500 shadow-[inset_0_-2px_0_0_#6366f1]'
                            : 'text-gray-400 hover:text-white hover:bg-white/5'
                            }`}
                    >
                        <CloudUpload size={20} />
                        Upload File
                    </button>
                    <button
                        onClick={() => setActiveTab('paste')}
                        className={`flex-1 py-4 px-6 flex items-center justify-center gap-2 font-semibold transition-all ${activeTab === 'paste'
                            ? 'bg-white/5 text-indigo-400 border-b-2 border-indigo-500 shadow-[inset_0_-2px_0_0_#6366f1]'
                            : 'text-gray-400 hover:text-white hover:bg-white/5'
                            }`}
                    >
                        <FileText size={20} />
                        Paste Text
                    </button>
                </div>

                {/* Content */}
                <div className="p-10">
                    <AnimatePresence mode="wait">
                        {activeTab === 'upload' ? (
                            <motion.div
                                key="upload"
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: 10 }}
                                className="space-y-6"
                            >
                                <div
                                    onDragOver={handleDragOver}
                                    onDragLeave={handleDragLeave}
                                    onDrop={handleDrop}
                                    className={`block border-2 border-dashed rounded-[40px] transition-all group ${selectedFiles.length > 0 ? 'p-8 pb-12' : 'p-12'
                                        } ${isDragging ? 'border-indigo-500 bg-indigo-500/10' : 'border-white/10 bg-white/5'
                                        } hover:border-indigo-500/50`}
                                >
                                    <div className="w-full text-center">
                                        <input
                                            id="file-upload-input"
                                            type="file"
                                            ref={fileInputRef}
                                            onChange={handleFileChange}
                                            className="hidden"
                                            accept=".pdf,.docx,.txt"
                                            multiple
                                        />

                                        {selectedFiles.length > 0 ? (
                                            <div className="space-y-6">
                                                <div className="flex flex-col gap-3">
                                                    <AnimatePresence>
                                                        {selectedFiles.map((item) => (
                                                            <motion.div
                                                                key={item.id}
                                                                initial={{ opacity: 0, y: 10 }}
                                                                animate={{ opacity: 1, y: 0 }}
                                                                exit={{ opacity: 0, scale: 0.95 }}
                                                                className="flex items-center justify-between p-5 bg-[#1e293b]/50 hover:bg-[#1e293b]/80 rounded-[20px] border border-white/5 shadow-lg text-left group/file transition-all"
                                                            >
                                                                <div className="flex items-center gap-4 overflow-hidden">
                                                                    <div className="w-12 h-12 bg-indigo-500/10 rounded-2xl flex items-center justify-center text-indigo-400 flex-shrink-0 border border-indigo-500/20">
                                                                        <FileText size={24} />
                                                                    </div>
                                                                    <div className="flex flex-col min-w-0">
                                                                        <span className="truncate text-base font-bold text-white">{item.file.name}</span>
                                                                        <span className="text-xs font-medium text-gray-500 lowercase">{(item.file.size / 1024 / 1024).toFixed(2)} MB</span>
                                                                    </div>
                                                                </div>
                                                                <button
                                                                    onClick={(e) => {
                                                                        e.preventDefault();
                                                                        e.stopPropagation();
                                                                        removeFile(item.id);
                                                                    }}
                                                                    className="p-2.5 hover:bg-red-500/10 text-gray-500 hover:text-red-400 rounded-xl transition-all opacity-0 group-hover/file:opacity-100"
                                                                    title="Remove file"
                                                                >
                                                                    <X size={20} />
                                                                </button>
                                                            </motion.div>
                                                        ))}
                                                    </AnimatePresence>
                                                </div>

                                                <div className="flex justify-center pt-4">
                                                    <label
                                                        htmlFor="file-upload-input"
                                                        className="px-10 py-3.5 rounded-2xl text-indigo-400 border-2 border-indigo-500/30 hover:border-indigo-500 bg-[#312e81]/10 hover:bg-indigo-500 hover:text-white font-black text-sm transition-all cursor-pointer shadow-xl hover:shadow-indigo-500/20 active:scale-95"
                                                    >
                                                        + Add Another File
                                                    </label>
                                                </div>
                                            </div>
                                        ) : (
                                            <label htmlFor="file-upload-input" className="cursor-pointer block">
                                                <div className="w-20 h-20 bg-white/5 rounded-[28px] shadow-sm border border-white/10 flex items-center justify-center mx-auto mb-6 group-hover:scale-110 transition-transform duration-500 group-hover:shadow-indigo-500/20">
                                                    <Upload className="text-indigo-400" size={40} />
                                                </div>
                                                <h3 className="text-3xl font-black text-white mb-3 tracking-tight">
                                                    Drop Intelligence
                                                </h3>
                                                <p className="text-gray-400 mb-8 font-medium italic text-lg opacity-80">
                                                    or click to ingest documents
                                                </p>
                                                <span className="bg-indigo-600 text-white px-12 py-4 rounded-2xl font-black text-xl hover:brightness-110 transition-all inline-block shadow-2xl shadow-indigo-900/40 active:scale-95">
                                                    Select Source
                                                </span>
                                            </label>
                                        )}
                                        <p className="text-[10px] font-black text-gray-600 uppercase tracking-[0.2em] mt-12 opacity-40">Standards: PDF, DOCX, TXT (Max 10MB)</p>
                                    </div>
                                </div>
                            </motion.div>
                        ) : (
                            <motion.div
                                key="paste"
                                initial={{ opacity: 0, x: 10 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -10 }}
                                className="space-y-4"
                            >
                                <div className="relative">
                                    <textarea
                                        value={text}
                                        onChange={(e) => setText(e.target.value)}
                                        placeholder="Paste your news article text here..."
                                        className="w-full h-64 p-6 bg-white/5 border border-white/10 rounded-2xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none text-white resize-none transition-all placeholder:text-gray-600"
                                    />
                                    <div className="absolute bottom-4 right-6 text-xs font-medium text-gray-400">
                                        {text.length} characters
                                    </div>
                                </div>

                                {/* Save As Settings */}
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4">
                                    <div className="space-y-2">
                                        <label className="flex items-center gap-2 text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">
                                            <Edit3 size={12} className="text-indigo-400" />
                                            Document Name
                                        </label>
                                        <input
                                            type="text"
                                            value={saveAsFileName}
                                            onChange={(e) => setSaveAsFileName(e.target.value)}
                                            placeholder="e.g. my-morning-report"
                                            className="w-full p-4 bg-white/5 border border-white/10 rounded-xl outline-none focus:ring-4 focus:ring-indigo-500/10 font-bold text-white shadow-sm transition-all"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="flex items-center gap-2 text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">
                                            <Type size={12} className="text-indigo-400" />
                                            Save Format
                                        </label>
                                        <div className="relative">
                                            <select
                                                value={saveAsFormat}
                                                onChange={(e) => setSaveAsFormat(e.target.value)}
                                                className="w-full p-4 bg-white/5 border border-white/10 rounded-xl outline-none focus:ring-4 focus:ring-indigo-500/10 font-bold text-white shadow-sm transition-all appearance-none cursor-pointer"
                                            >
                                                <option value="txt" className="bg-[#0f172a]">Plain Text (.txt)</option>
                                                <option value="pdf" className="bg-[#0f172a]">PDF Document (.pdf)</option>
                                                <option value="docx" className="bg-[#0f172a]">Word Document (.docx)</option>
                                            </select>
                                            <ChevronDown size={18} className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
                                        </div>
                                    </div>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* Status Messages */}
                    {(error || success) && (
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className={`mt-6 p-4 rounded-xl flex items-center gap-3 ${error ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                }`}
                        >
                            {error ? <AlertCircle size={20} /> : <FileCheck size={20} />}
                            <p className="text-sm font-semibold">{error || success}</p>
                        </motion.div>
                    )}

                    {/* Progress Bar (Visible when uploading) */}
                    <div className={`mt-8 transition-all duration-500 overflow-hidden ${isUploading ? 'h-1.5' : 'h-0'}`}>
                        <div className="w-full bg-white/5 rounded-full h-full">
                            <motion.div
                                initial={{ width: 0 }}
                                animate={isUploading ? { width: '100%' } : { width: 0 }}
                                transition={{ duration: 2 }}
                                className="bg-indigo-600 h-full rounded-full"
                            />
                        </div>
                    </div>

                    {/* Action Button */}
                    <div className="mt-10 flex justify-center">
                        <button
                            onClick={handleAnalyze}
                            disabled={isUploading}
                            className="bg-emerald-600 text-white px-10 py-4 rounded-2xl font-black text-xl flex items-center gap-3 relative overflow-hidden group shadow-xl shadow-emerald-500/20 hover:brightness-110 active:scale-95 transition-all disabled:opacity-50"
                        >
                            {isUploading ? (
                                <>
                                    <Loader2 size={24} className="animate-spin" />
                                    Saving...
                                </>
                            ) : (
                                <>
                                    <Sparkles size={24} />
                                    Upload Now
                                </>
                            )}
                            <div className="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </button>
                    </div>
                </div>
            </div>

            {/* Trust Badges */}
            <div className="mt-8 flex items-center justify-center gap-8 text-gray-500 grayscale opacity-30">
                <span className="text-sm font-bold tracking-widest uppercase">Trusted By</span>
                <div className="flex gap-6 items-center">
                    <div className="h-4 w-24 bg-white/10 rounded" />
                    <div className="h-4 w-20 bg-white/10 rounded" />
                    <div className="h-4 w-28 bg-white/10 rounded" />
                </div>
            </div>
        </motion.div>
    );
}
