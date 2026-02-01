import { motion } from 'framer-motion';
import {
    Instagram,
    Facebook,
    Twitter,
    Mail,
    Phone,
    MapPin,
    Users,
    ShieldCheck,
    Zap,
    Github
} from 'lucide-react';

const socialLinks = [
    { id: 'instagram', icon: <Instagram size={24} />, label: 'Instagram', color: 'hover:text-pink-400 hover:bg-pink-400/10', url: '#' },
    { id: 'facebook', icon: <Facebook size={24} />, label: 'Facebook', color: 'hover:text-blue-400 hover:bg-blue-400/10', url: '#' },
    { id: 'twitter', icon: <Twitter size={24} />, label: 'X (Twitter)', color: 'hover:text-indigo-400 hover:bg-indigo-400/10', url: '#' },
    { id: 'github', icon: <Github size={24} />, label: 'GitHub', color: 'hover:text-white hover:bg-white/10', url: '#' },
];

const contactDetails = [
    { id: 'email', icon: <Mail className="text-indigo-400" size={20} />, label: 'Email Us', value: 'hello@tazakhabar.ai' },
    { id: 'phone', icon: <Phone className="text-green-400" size={20} />, label: 'Call Us', value: '+1 (555) 000-0000' },
    { id: 'location', icon: <MapPin className="text-orange-400" size={20} />, label: 'Headquarters', value: 'Silicon Valley, CA' },
];

export default function About() {
    return (
        <div className="pb-20 pt-32 max-w-5xl mx-auto px-4">
            {/* Hero Section */}
            <section className="text-center mb-20">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-indigo-500/10 text-indigo-400 text-sm font-bold border border-indigo-500/20 mb-6"
                >
                    <Users size={16} /> Our Story
                </motion.div>
                <motion.h1
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="text-5xl font-black text-white mb-6 tracking-tight leading-tight"
                >
                    Redefining News Analysis <br /> with <span className="text-indigo-500">Advanced AI</span>
                </motion.h1>
                <motion.p
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="text-gray-400 text-xl max-w-2xl mx-auto leading-relaxed"
                >
                    Taza Khabar is dedicated to providing high-fidelity, real-time news intelligence through cutting-edge natural language processing and hybrid algorithms.
                </motion.p>
            </section>

            {/* Grid Content */}
            <div className="grid md:grid-cols-2 gap-12 mb-20">
                {/* Contact & Socials */}
                <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.3 }}
                    className="space-y-8"
                >
                    <div>
                        <h2 className="text-2xl font-black text-white mb-6">Get in Touch</h2>
                        <div className="grid gap-4">
                            {contactDetails.map((contact) => (
                                <div key={contact.id} className="p-6 bg-white/5 backdrop-blur-md border border-white/10 rounded-[32px] flex items-center gap-6 group hover:bg-white/10 transition-all">
                                    <div className="w-12 h-12 bg-white/5 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                                        {contact.icon}
                                    </div>
                                    <div>
                                        <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-1">{contact.label}</p>
                                        <p className="text-lg font-bold text-white">{contact.value}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div>
                        <h2 className="text-2xl font-black text-white mb-6">Follow Our Journey</h2>
                        <div className="flex flex-wrap gap-4">
                            {socialLinks.map((social) => (
                                <a
                                    key={social.id}
                                    href={social.url}
                                    className={`flex items-center gap-3 px-6 py-4 bg-white/5 border border-white/10 rounded-2xl transition-all font-bold text-gray-400 ${social.color} hover:shadow-xl hover:shadow-indigo-500/10`}
                                >
                                    {social.icon}
                                    {social.label}
                                </a>
                            ))}
                        </div>
                    </div>
                </motion.div>

                {/* Vision Section */}
                <motion.div
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.4 }}
                    className="bg-white/5 backdrop-blur-xl rounded-[48px] p-12 border border-white/10 relative overflow-hidden"
                >
                    <div className="absolute top-[-10%] right-[-10%] w-64 h-64 bg-indigo-500/20 rounded-full blur-3xl opacity-50" />
                    <div className="relative z-10 space-y-8">
                        <div className="w-16 h-16 bg-white/5 border border-white/10 rounded-3xl flex items-center justify-center text-indigo-400 shadow-xl">
                            <ShieldCheck size={32} />
                        </div>
                        <h2 className="text-3xl font-black text-white leading-tight">Our Commitment to Accuracy</h2>
                        <p className="text-gray-400 leading-relaxed text-lg font-medium">
                            We believe that in an era of information overload, clarity is power. Our platform uses multi-layered verification to ensure that every keyword, sentiment, and summary is grounded in the source text with over 95% measured confidence.
                        </p>
                        <div className="grid grid-cols-2 gap-6 pt-6">
                            <div className="p-6 bg-white/5 rounded-[32px] border border-white/10">
                                <Zap className="text-indigo-400 mb-3" size={24} />
                                <p className="text-2xl font-black text-white">0.07s</p>
                                <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Avg. Processing</p>
                            </div>
                            <div className="p-6 bg-white/5 rounded-[32px] border border-white/10">
                                <ShieldCheck className="text-green-400 mb-3" size={24} />
                                <p className="text-2xl font-black text-white">99.1%</p>
                                <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Confidence Score</p>
                            </div>
                        </div>
                    </div>
                </motion.div>
            </div>
        </div>
    );
}
