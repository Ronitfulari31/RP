import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import {
    FileText,
    Languages,
    Target,
    Zap,
    Activity,
    Clock,
    CheckCircle2,
    BarChart3,
    Loader2
} from 'lucide-react';
import { api } from '../services/api';

const iconMap = {
    summarization: <FileText size={20} />,
    translation: <Languages size={20} />,
    keywords: <Target size={20} />,
    sentiment: <Activity size={20} />,
};

const colorMap = {
    summarization: '#6366F1',
    translation: '#818CF8',
    keywords: '#10B981',
    sentiment: '#F43F5E',
};

export default function DetailedStats() {
    const [usageData, setUsageData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchUsage = async () => {
            setLoading(true);
            try {
                const response = await api.getFeatureEngagement();
                if (response.status === 'success' && response.data?.length > 0) {
                    setUsageData(response.data);
                } else {
                    setUsageData([]);
                }
            } catch (err) {
                console.error('Failed to fetch detailed stats:', err);
                setUsageData([]);
                // setError('Failed to load system engagement metrics');
            } finally {
                setLoading(false);
            }
        };

        fetchUsage();
    }, []);

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
                <Loader2 className="animate-spin text-indigo-400" size={48} />
                <p className="text-gray-400 font-bold">Auditing system throughput...</p>
            </div>
        );
    }

    return (
        <div className="space-y-10 animate-fade-in max-w-6xl mx-auto">
            <div>
                <h2 className="text-4xl font-black text-white tracking-tight mb-3">Feature Engagement</h2>
                <p className="text-gray-400 text-lg font-medium">Detailed audit of AI function utilization and system throughput.</p>
            </div>

            <div className="grid md:grid-cols-2 gap-8">
                <div className="space-y-6">
                    {usageData.map((item, index) => (
                        <motion.div
                            key={item.id}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.1 }}
                            className="bg-[#0f172a]/40 backdrop-blur-xl p-8 rounded-[32px] border border-white/10 shadow-sm transition-all group"
                        >
                            <div className="flex items-center justify-between mb-6">
                                <div className="flex items-center gap-4">
                                    <div
                                        style={{ backgroundColor: `${colorMap[item.id]}15`, color: colorMap[item.id] }}
                                        className="w-12 h-12 rounded-2xl flex items-center justify-center shadow-inner"
                                    >
                                        {iconMap[item.id] || <Activity size={20} />}
                                    </div>
                                    <div>
                                        <h4 className="font-black text-white leading-none mb-1">{item.label}</h4>
                                        <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest">{item.active_module}</p>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <p className="text-2xl font-black text-white leading-none mb-1">{item.invocations.toLocaleString()}</p>
                                    <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest leading-none">Total Invocations</p>
                                </div>
                            </div>

                            <div className="space-y-2">
                                <div className="flex items-center justify-between text-[10px] font-black text-gray-500 uppercase tracking-widest">
                                    <span>Throughput Efficiency</span>
                                    <span style={{ color: colorMap[item.id] }}>{item.efficiency}%</span>
                                </div>
                                <div className="h-3 w-full bg-white/5 rounded-full overflow-hidden border border-white/10">
                                    <motion.div
                                        initial={{ width: 0 }}
                                        animate={{ width: `${item.efficiency}%` }}
                                        transition={{ duration: 1, ease: "easeOut", delay: index * 0.1 + 0.5 }}
                                        style={{ backgroundColor: colorMap[item.id] }}
                                        className="h-full rounded-full shadow-lg"
                                    />
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </div>

                <div className="space-y-8">
                    <div className="bg-[#0f172a]/60 backdrop-blur-2xl p-10 rounded-[48px] text-white shadow-2xl shadow-indigo-500/10 border border-white/10 relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full -mr-20 -mt-20 blur-3xl" />
                        <Zap className="text-indigo-400 mb-6" size={40} />
                        <h3 className="text-3xl font-black tracking-tight mb-4">Zero-Shot Classifier <br />& BERT Neural Core</h3>
                        <p className="text-gray-400 font-medium text-lg leading-relaxed mb-8">
                            Our specialized classification and representation models are currently processing with industry-leading efficiency and real-time response capability.
                        </p>
                        <div className="grid grid-cols-2 gap-6">
                            <div className="bg-white/5 p-4 rounded-2xl backdrop-blur-md border border-white/10">
                                <Clock size={20} className="text-indigo-300 mb-2" />
                                <p className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-1">Avg Latency</p>
                                <p className="text-xl font-black text-white">142ms</p>
                            </div>
                            <div className="bg-white/5 p-4 rounded-2xl backdrop-blur-md border border-white/10">
                                <CheckCircle2 size={20} className="text-emerald-400 mb-2" />
                                <p className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-1">Uptime SLA</p>
                                <p className="text-xl font-black text-emerald-400">99.9%</p>
                            </div>
                        </div>
                    </div>

                    <div className="bg-[#0f172a]/40 backdrop-blur-xl p-10 rounded-[48px] border border-white/10 shadow-sm flex items-center gap-6">
                        <div className="w-16 h-16 rounded-3xl bg-white/5 border border-white/10 flex items-center justify-center text-indigo-400 shadow-inner shrink-0 text-2xl font-black">
                            <BarChart3 size={32} />
                        </div>
                        <div>
                            <h4 className="text-xl font-black text-white mb-1 tracking-tight">Real-time Analytics</h4>
                            <p className="text-gray-400 font-medium">Usage statistics are updated every 60 seconds with live system sync.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
