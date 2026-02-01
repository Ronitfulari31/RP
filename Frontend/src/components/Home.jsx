import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, BarChart3, Languages, FileText, ArrowRight, Zap, Target, Globe } from 'lucide-react';
import { api } from '../services/api';

const features = [
    // ... same features ...
];

export default function Home({ onGetStarted }) {
    const [error, setError] = useState('');
    const [stats, setStats] = useState([
        { label: 'Articles Analyzed', value: '...' },
        { label: 'Languages', value: '...' },
        { label: 'Accuracy Rate', value: '...' },
        { label: 'Active Users', value: '...' }
    ]);

    useEffect(() => {
        const fetchStats = async () => {
            try {
                const response = await api.getGlobalStats();
                if (response.status === 'success') {
                    const data = response.data;
                    setStats([
                        { label: 'Articles Analyzed', value: data.articles_analyzed },
                        { label: 'Languages', value: data.languages },
                        { label: 'Accuracy Rate', value: data.accuracy_rate },
                        { label: 'Active Users', value: data.active_users }
                    ]);
                }
            } catch (err) {
                console.error('Failed to fetch global stats:', err);
                setError('Failed to load real-time statistics.');
            }
        };
        fetchStats();
    }, []);

    return (
        <div className="pt-32 pb-20 px-4">
            {error && (
                <div className="max-w-xl mx-auto mb-8 p-4 bg-red-500/10 text-red-400 rounded-2xl border border-red-500/20 text-center animate-shake">
                    {error}
                </div>
            )}
            {/* Hero Section */}
            <section className="text-center mb-24">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                >
                    <span className="px-4 py-1.5 rounded-full bg-indigo-500/10 text-indigo-300 text-sm font-semibold mb-6 inline-block border border-indigo-500/20">
                        <Sparkles className="inline-block mr-2 text-indigo-400" size={16} />
                        The Future of News Intelligence
                    </span>
                    <h1 className="text-5xl md:text-7xl font-extrabold text-white tracking-tight mb-8 leading-tight">
                        Master the News Flow with <br />
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-emerald-400">
                            InsightPoint AI
                        </span>
                    </h1>
                    <p className="text-xl text-gray-400 max-w-3xl mx-auto leading-relaxed mb-12">
                        Revolutionize how you consume news. Our AI suite offers real-time sentiment analysis,
                        intelligent summarization, and seamless translation across multiple languages.
                    </p>
                    <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                        <button
                            onClick={onGetStarted}
                            className="btn-primary py-4 px-8 text-lg flex items-center gap-2 group shadow-xl shadow-indigo-500/20 bg-indigo-600 hover:bg-indigo-500 text-white rounded-2xl font-bold transition-all"
                        >
                            Get Started for Free
                            <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
                        </button>
                        <button className="px-8 py-4 text-lg font-semibold text-gray-400 hover:text-white transition-colors">
                            How it Works
                        </button>
                    </div>
                </motion.div>
            </section>

            {/* Stats/Social Proof */}
            <motion.div
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="max-w-5xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 mb-24 border-y border-white/10 py-12"
            >
                {stats.map((stat, i) => (
                    <div key={i} className="text-center">
                        <p className="text-3xl font-bold text-white">{stat.value}</p>
                        <p className="text-sm text-gray-500 font-medium uppercase tracking-wider">{stat.label}</p>
                    </div>
                ))}
            </motion.div>

            {/* Features Grid */}
            <section className="max-w-6xl mx-auto">
                <div className="text-center mb-16">
                    <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">Powerful Features for Deep Insights</h2>
                    <p className="text-gray-400">Everything you need to stay ahead of the curve.</p>
                </div>

                <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
                    {features.map((feature, index) => (
                        <motion.div
                            key={index}
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.1 }}
                            viewport={{ once: true }}
                            className="p-8 rounded-3xl bg-white/5 backdrop-blur-sm border border-white/10 hover:border-indigo-500/30 hover:shadow-2xl hover:shadow-indigo-500/10 transition-all duration-300 group"
                        >
                            <div className={`w-14 h-14 ${feature.color} rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300`}>
                                {feature.icon}
                            </div>
                            <h3 className="text-xl font-bold text-white mb-3">{feature.title}</h3>
                            <p className="text-gray-400 leading-relaxed text-sm">
                                {feature.description}
                            </p>
                        </motion.div>
                    ))}
                </div>
            </section>
        </div>
    );
}
