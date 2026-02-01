import { useState, useEffect, useRef } from 'react';
import {
    PieChart,
    Pie,
    Cell,
    ResponsiveContainer,
    Tooltip,
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Legend,
} from 'recharts';
import {
    Smile,
    Frown,
    Shuffle,
    TrendingUp,
    BarChart3,
    Loader2
} from 'lucide-react';
import { api } from '../services/api';

export default function AnalyticsReports({ setActiveTab }) {
    const [sentimentData, setSentimentData] = useState([
        { name: 'Positive', value: 0, color: '#10B981' },
        { name: 'Neutral', value: 0, color: '#6366F1' },
        { name: 'Negative', value: 0, color: '#F43F5E' },
    ]);

    const [sentimentTrendData, setSentimentTrendData] = useState([]);
    const [totalReports, setTotalReports] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchAnalytics = async () => {
            setLoading(true);
            try {
                // Fetch distribution
                const distResponse = await api.getSentimentDistribution();
                let distData = { positive: 0, neutral: 0, negative: 0 };
                if (distResponse.status === 'success') {
                    distData = distResponse.data;
                }

                const total = (distData.positive || 0) + (distData.neutral || 0) + (distData.negative || 0);
                setTotalReports(total);
                setSentimentData([
                    { name: 'Positive', value: distData.positive || 0, color: '#10B981' },
                    { name: 'Neutral', value: distData.neutral || 0, color: '#6366F1' },
                    { name: 'Negative', value: distData.negative || 0, color: '#F43F5E' },
                ]);

                // Fetch trends
                const trendResponse = await api.getSentimentTrend('daily', 168); // 7 days
                let trendData = [];
                if (trendResponse.status === 'success' && trendResponse.data?.length > 0) {
                    trendData = trendResponse.data;
                }

                const mappedTrends = trendData.map(item => ({
                    name: new Date(item.time).toLocaleDateString(undefined, { weekday: 'short' }),
                    positive: item.positive,
                    neutral: item.neutral,
                    negative: item.negative
                }));
                setSentimentTrendData(mappedTrends);
            } catch (err) {
                console.error('Failed to fetch analytics:', err);
                setError('Failed to load real-time analytics');
            } finally {
                setLoading(false);
            }
        };

        fetchAnalytics();
    }, []);

    const positivePercent = totalReports > 0
        ? Math.round((sentimentData.find(d => d.name === 'Positive').value / totalReports) * 100)
        : 0;

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
                <Loader2 className="animate-spin text-indigo-400" size={48} />
                <p className="text-gray-400 font-bold">Synchronizing analysis data...</p>
            </div>
        );
    }

    return (
        <div className="space-y-10 animate-fade-in max-w-6xl mx-auto">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                <div>
                    <h2 className="text-4xl font-black text-white tracking-tight mb-3">Sentiment Insights</h2>
                    <p className="text-gray-400 text-lg font-medium">Linguistic emotional distribution across processed intelligence.</p>
                </div>
                <div className="flex flex-wrap items-center gap-4">
                    <button
                        onClick={() => setActiveTab('upload')}
                        className="flex items-center gap-2 bg-indigo-600 text-white px-5 py-2.5 rounded-xl font-bold hover:shadow-lg hover:shadow-indigo-500/20 transition-all active:scale-95"
                    >
                        <BarChart3 size={18} />
                        Upload Intelligence
                    </button>
                    <div className="flex items-center gap-3 bg-emerald-500/10 px-4 py-2 rounded-xl border border-emerald-500/20">
                        <TrendingUp size={18} className="text-emerald-400" />
                        <span className="text-sm font-bold text-emerald-400">{positivePercent}% Positive Reach</span>
                    </div>
                </div>
            </div>

            <div className="grid lg:grid-cols-2 gap-8">
                {/* Sentiment Distribution Pie Chart */}
                <div className="bg-[#0f172a]/40 backdrop-blur-xl p-8 rounded-[48px] border border-white/10 shadow-sm space-y-8 flex flex-col items-center">
                    <div className="w-full">
                        <h3 className="text-xl font-black text-white tracking-tight">Distribution Overview</h3>
                        <p className="text-sm font-medium text-gray-400">Current sentiment volume breakdown</p>
                    </div>

                    <div className="h-[300px] w-full relative">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={sentimentData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={80}
                                    outerRadius={110}
                                    paddingAngle={8}
                                    dataKey="value"
                                >
                                    {sentimentData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} stroke="none" />
                                    ))}
                                </Pie>
                                <Tooltip
                                    contentStyle={{
                                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                                        borderRadius: '24px',
                                        border: '1px solid rgba(255, 255, 255, 0.1)',
                                        backdropFilter: 'blur(8px)',
                                        fontWeight: 'bold',
                                        color: '#fff'
                                    }}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                            <span className="text-4xl font-black text-white leading-none">{totalReports}</span>
                            <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest mt-1">Total Reports</span>
                        </div>
                    </div>

                    <div className="w-full grid grid-cols-3 gap-4">
                        <SentimentStat
                            label="Positive"
                            color="#10B981"
                            icon={<Smile size={14} />}
                            value={totalReports > 0 ? Math.round((sentimentData[0].value / totalReports) * 100) : 0}
                        />
                        <SentimentStat
                            label="Neutral"
                            color="#6366F1"
                            icon={<Shuffle size={14} />}
                            value={totalReports > 0 ? Math.round((sentimentData[1].value / totalReports) * 100) : 0}
                        />
                        <SentimentStat
                            label="Negative"
                            color="#F43F5E"
                            icon={<Frown size={14} />}
                            value={totalReports > 0 ? Math.round((sentimentData[2].value / totalReports) * 100) : 0}
                        />
                    </div>
                </div>

                {/* Sentiment Trend Line Chart */}
                <div className="bg-[#0f172a]/40 backdrop-blur-xl p-8 rounded-[48px] border border-white/10 shadow-sm space-y-8">
                    <div>
                        <h3 className="text-xl font-black text-white tracking-tight">Sentiment Trends</h3>
                        <p className="text-sm font-medium text-gray-400">Weekly emotional progression tracking</p>
                    </div>

                    <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={sentimentTrendData}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                                <XAxis
                                    dataKey="name"
                                    axisLine={false}
                                    tickLine={false}
                                    tick={{ fontSize: 12, fontWeight: 700, fill: '#94a3b8' }}
                                    dy={10}
                                />
                                <YAxis
                                    axisLine={false}
                                    tickLine={false}
                                    tick={{ fontSize: 12, fontWeight: 700, fill: '#94a3b8' }}
                                />
                                <Tooltip
                                    contentStyle={{
                                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                                        borderRadius: '24px',
                                        border: '1px solid rgba(255, 255, 255, 0.1)',
                                        backdropFilter: 'blur(8px)',
                                        fontWeight: 'bold',
                                        color: '#fff'
                                    }}
                                />
                                <Legend wrapperStyle={{ paddingTop: '20px' }} />
                                <Line type="monotone" dataKey="positive" name="Positive" stroke="#10B981" strokeWidth={4} dot={{ r: 4, fill: '#10B981', strokeWidth: 2, stroke: '#fff' }} activeDot={{ r: 6 }} />
                                <Line type="monotone" dataKey="neutral" name="Neutral" stroke="#6366F1" strokeWidth={4} dot={{ r: 4, fill: '#6366F1', strokeWidth: 2, stroke: '#fff' }} activeDot={{ r: 6 }} />
                                <Line type="monotone" dataKey="negative" name="Negative" stroke="#F43F5E" strokeWidth={4} dot={{ r: 4, fill: '#F43F5E', strokeWidth: 2, stroke: '#fff' }} activeDot={{ r: 6 }} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>
        </div>
    );
}

function SentimentStat({ label, color, icon, value }) {
    return (
        <div className="text-center p-4 rounded-3xl bg-white/5 border border-white/10 transition-all hover:bg-white/10">
            <div style={{ color }} className="flex justify-center mb-2">{icon}</div>
            <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-1">{label}</p>
            <p className="text-lg font-black text-white">{value}%</p>
        </div>
    );
}
