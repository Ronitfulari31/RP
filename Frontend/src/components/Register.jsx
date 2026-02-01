import { useState, useRef, useEffect } from 'react';
import { useGoogleLogin } from '@react-oauth/google';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '../services/api';
import {
    Mail,
    Lock,
    User,
    ArrowRight,
    Chrome,
    Github,
    Phone,
    Loader2,
    Eye,
    EyeOff,
    ChevronDown
} from 'lucide-react';
import InteractiveBackground from './InteractiveBackground';

const countries = [
    { code: '+91', country: 'IN', flag: 'https://flagcdn.com/w20/in.png' },
    { code: '+1', country: 'US', flag: 'https://flagcdn.com/w20/us.png' },
    { code: '+44', country: 'GB', flag: 'https://flagcdn.com/w20/gb.png' },
    { code: '+1', country: 'CA', flag: 'https://flagcdn.com/w20/ca.png' },
    { code: '+61', country: 'AU', flag: 'https://flagcdn.com/w20/au.png' }
];

export default function Register({ onRegister, onSwitchToLogin }) {
    const [isLoading, setIsLoading] = useState(false);

    const [showPassword, setShowPassword] = useState(false);
    const [selectedCountry, setSelectedCountry] = useState(countries[0]);
    const [showCountryDropdown, setShowCountryDropdown] = useState(false);

    const [formData, setFormData] = useState({
        username: '',
        email: '',
        password: '',
        phone: ''
    });
    const [error, setError] = useState('');

    const googleLogin = useGoogleLogin({
        onSuccess: async (tokenResponse) => {
            setIsLoading(true);
            setError('');

            try {
                const response = await api.googleAuth({ access_token: tokenResponse.access_token });
                localStorage.setItem('token', response.token);
                localStorage.setItem('user', JSON.stringify(response.user));
                onRegister();
            } catch (err) {
                setError(err.message || 'Google authentication failed');
            } finally {
                setIsLoading(false);
            }
        },
        onError: () => setError('Google sign-in failed'),
    });



    const handleRegister = async (e) => {
        e.preventDefault();
        setError('');

        setIsLoading(true);
        try {
            await api.register(formData.username, formData.email, formData.password, formData.phone);
            const loginRes = await api.login(formData.username, formData.password);
            localStorage.setItem('token', loginRes.data.token);
            localStorage.setItem('user', JSON.stringify(loginRes.data.user));

            setIsLoading(false);
            onRegister();
        } catch (err) {
            setError(err.message);
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center p-6 relative overflow-hidden text-white">
            <InteractiveBackground />

            <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ duration: 0.4, ease: "easeOut" }}
                className="w-full max-w-xl bg-white/5 backdrop-blur-xl rounded-[48px] shadow-2xl shadow-indigo-500/10 border border-white/10 p-10 md:p-12 z-10 relative"
            >
                <div className="text-center mb-10">
                    <div className="w-16 h-16 rounded-2xl overflow-hidden mx-auto mb-6 shadow-xl border-4 border-white/10">
                        <img src="/logo.jpeg" alt="Logo" className="w-full h-full object-cover" />
                    </div>
                    <h1 className="text-3xl font-black text-white tracking-tight mb-2">Create Account</h1>
                    <p className="text-gray-400 font-medium">Join 10k+ analysts scaling their intelligence.</p>
                </div>

                <form onSubmit={handleRegister} className="space-y-6">
                    <div className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-xs font-bold text-gray-400 uppercase tracking-widest ml-1">Username</label>
                            <div className="relative group">
                                <User className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-indigo-400 transition-colors" size={18} />
                                <input
                                    type="text"
                                    placeholder="Username"
                                    required
                                    value={formData.username}
                                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                                    className="w-full pl-12 pr-6 py-4 bg-white/5 border border-white/10 rounded-2xl outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all font-medium text-white placeholder-gray-500 focus:bg-white/10"
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-xs font-bold text-gray-400 uppercase tracking-widest ml-1">Email Address</label>
                            <div className="relative group">
                                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-indigo-400 transition-colors" size={18} />
                                <input
                                    type="email"
                                    placeholder="Email"
                                    required
                                    value={formData.email}
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                    className="w-full pl-12 pr-6 py-4 bg-white/5 border border-white/10 rounded-2xl outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all font-medium text-white placeholder-gray-500 focus:bg-white/10"
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-xs font-bold text-gray-400 uppercase tracking-widest ml-1">Phone Number</label>
                            <div className="relative group">
                                <div className="absolute left-4 top-1/2 -translate-y-1/2 flex items-center gap-2 border-r border-white/10 pr-2 mr-3 text-gray-400 font-bold cursor-pointer hover:text-white transition-colors" onClick={() => setShowCountryDropdown(!showCountryDropdown)}>
                                    <img src={selectedCountry.flag} alt={selectedCountry.country} className="w-5 rounded-sm" />
                                    <span>{selectedCountry.code}</span>
                                    <ChevronDown size={14} className="text-gray-400" />
                                </div>

                                {/* Country Dropdown */}
                                {showCountryDropdown && (
                                    <div className="absolute top-14 left-0 bg-[#0f172a] border border-white/10 rounded-xl shadow-xl z-50 w-40 overflow-hidden">
                                        {countries.map((country, index) => (
                                            <button
                                                key={index}
                                                type="button"
                                                onClick={() => {
                                                    setSelectedCountry(country);
                                                    setShowCountryDropdown(false);
                                                }}
                                                className="w-full flex items-center gap-3 px-4 py-3 hover:bg-white/5 transition-colors text-sm font-medium text-gray-300 hover:text-white"
                                            >
                                                <img src={country.flag} alt={country.country} className="w-5 rounded-sm" />
                                                {country.code}
                                            </button>
                                        ))}
                                    </div>
                                )}

                                <input
                                    type="tel"
                                    placeholder="xxxxx-xxxxx"
                                    required
                                    value={formData.phone}
                                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                                    className="w-full pl-36 pr-6 py-4 bg-white/5 border border-white/10 rounded-2xl outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all font-medium text-white placeholder-gray-500 focus:bg-white/10"
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-xs font-bold text-gray-400 uppercase tracking-widest ml-1">Create Password</label>
                            <div className="relative group">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-indigo-400 transition-colors" size={18} />
                                <input
                                    type={showPassword ? "text" : "password"}
                                    placeholder="Min. 8 characters"
                                    required
                                    value={formData.password}
                                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                    className="w-full pl-12 pr-12 py-4 bg-white/5 border border-white/10 rounded-2xl outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all font-medium text-white placeholder-gray-500 focus:bg-white/10"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200 transition-colors"
                                >
                                    {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                                </button>
                            </div>
                        </div>
                    </div>

                    {error && (
                        <p className="text-red-400 text-xs font-bold bg-red-500/10 p-3 rounded-xl border border-red-500/20 italic">
                            ⚠️ {error}
                        </p>
                    )}

                    <button
                        type="submit"
                        disabled={isLoading}
                        className="w-full py-4 bg-indigo-600 text-white rounded-2xl font-black text-lg shadow-xl shadow-indigo-500/30 hover:bg-indigo-500 hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center justify-center gap-3 mt-4 disabled:opacity-70"
                    >
                        {isLoading ? (
                            <Loader2 className="animate-spin" size={20} />
                        ) : (
                            <>
                                Create Account
                                <ArrowRight size={20} />
                            </>
                        )}
                    </button>
                </form>

                {/* Divider */}
                <div className="relative my-10">
                    <div className="absolute inset-0 flex items-center">
                        <div className="w-full border-t border-white/10"></div>
                    </div>
                    <div className="relative flex justify-center text-xs uppercase tracking-widest font-bold text-gray-400">
                        <span className="bg-[#0f172a]/50 px-4 backdrop-blur-sm rounded-full">Or sign up with</span>
                    </div>
                </div>

                {/* Social Register */}
                <div className="space-y-4">
                    <button
                        type="button"
                        onClick={() => googleLogin()}
                        className="w-full flex items-center justify-center gap-3 py-4 border border-white/10 rounded-2xl font-bold text-gray-300 hover:bg-white/5 hover:text-white transition-all group bg-white/5"
                    >
                        <Chrome size={20} className="text-red-500 group-hover:scale-110 transition-transform" />
                        Continue with Google
                    </button>
                </div>

                <p className="text-center mt-10 text-sm font-medium text-gray-400">
                    Already have an account?{' '}
                    <button
                        type="button"
                        onClick={onSwitchToLogin}
                        className="text-indigo-400 font-black hover:text-indigo-300 hover:underline"
                    >
                        Sign In
                    </button>
                </p>
            </motion.div>

            <div className="absolute top-10 left-10 hidden lg:block z-10">
                <p className="text-[10px] font-black text-gray-500 uppercase tracking-[0.2em] [writing-mode:vertical-lr] rotate-180">
                    Secure Registration Portal
                </p>
            </div>
        </div >
    );
}
