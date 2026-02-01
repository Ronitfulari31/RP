import { useState, useRef, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  User,
  ChevronDown,
  Activity,
  Settings,
  Lock,
  LogOut,
  Mail,
  ShieldCheck
} from 'lucide-react';

export default function Header({ onLogout }) {
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const dropdownRef = useRef(null);
  const location = useLocation();

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsProfileOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Helper to check if current page
  const isActive = (path) => location.pathname === path;

  const [userData, setUserData] = useState({
    username: 'User',
    email: '',
    role: 'Member',
    access: 'Standard Access'
  });

  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      try {
        const parsed = JSON.parse(storedUser);
        setUserData({
          username: parsed.username || 'User',
          email: parsed.email || '',
          role: parsed.role || 'Member',
          access: parsed.role === 'admin' ? 'Administrator Access' : 'Standard Access'
        });
      } catch (err) {
        console.error('Failed to parse user data:', err);
      }
    }

    // Listener for profile updates from Settings
    const handleProfileUpdate = () => {
      const updatedUser = localStorage.getItem('user');
      if (updatedUser) {
        try {
          const parsed = JSON.parse(updatedUser);
          setUserData({
            username: parsed.username || 'User',
            email: parsed.email || '',
            role: parsed.role || 'Member',
            access: parsed.role === 'admin' ? 'Administrator Access' : 'Standard Access'
          });
        } catch (err) {
          console.error('Failed to parse updated user data:', err);
        }
      }
    };

    window.addEventListener('user-profile-updated', handleProfileUpdate);
    return () => window.removeEventListener('user-profile-updated', handleProfileUpdate);
  }, []);

  const getInitials = (name) => {
    return name && typeof name === 'string' ? name.charAt(0).toUpperCase() : 'U';
  };

  return (
    <header className="fixed top-0 left-0 right-0 h-20 bg-[#0f172a]/80 backdrop-blur-md border-b border-white/10 z-50 px-8 flex items-center justify-between">
      <Link to="/" className="flex items-center gap-3 cursor-pointer group">
        <div className="w-12 h-12 rounded-2xl overflow-hidden border-2 border-white/10 shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform duration-300">
          <img src="/logo.jpeg" alt="InsightPoint Logo" className="w-full h-full object-cover" />
        </div>
        <span className="text-xl font-bold tracking-tight text-white group-hover:text-indigo-400 transition-colors">InsightPoint</span>
      </Link>

      {/* Centered Navigation */}
      <nav className="hidden md:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 items-center gap-10">
        <Link
          to="/"
          className={`text-lg font-bold transition-all ${isActive('/') ? 'text-indigo-400 scale-105' : 'text-gray-400 hover:text-white hover:scale-105'}`}
        >
          Home
        </Link>
        <Link
          to="/analyze"
          className={`text-lg font-bold transition-all ${isActive('/analyze') ? 'text-indigo-400 scale-105' : 'text-gray-400 hover:text-white hover:scale-105'}`}
        >
          Analyze
        </Link>
        <Link
          to="/news"
          className={`text-lg font-bold transition-all ${isActive('/news') ? 'text-indigo-400 scale-105' : 'text-gray-400 hover:text-white hover:scale-105'}`}
        >
          News Feed
        </Link>
        <Link
          to="/about"
          className={`text-lg font-bold transition-all ${isActive('/about') ? 'text-indigo-400 scale-105' : 'text-gray-400 hover:text-white hover:scale-105'}`}
        >
          About
        </Link>
      </nav>

      {/* Right Side: Profile */}
      <div className="flex items-center gap-4">

        <div className="flex items-center gap-3 pl-6 border-l border-white/10 relative" ref={dropdownRef}>
          <div className="text-right hidden sm:block">
            <p className="text-sm font-bold text-white leading-none">{userData.username}</p>
            <p className="text-[10px] text-gray-400 font-bold uppercase tracking-widest mt-1">{userData.role}</p>
          </div>

          <button
            onClick={() => setIsProfileOpen(!isProfileOpen)}
            className="relative group cursor-pointer focus:outline-none"
          >
            <div className={`w-10 h-10 rounded-full border-2 transition-all flex items-center justify-center text-sm font-black text-white ${isProfileOpen ? 'border-indigo-500 bg-indigo-600' : 'border-white/10 bg-indigo-600/80 group-hover:border-white/30'}`}>
              {getInitials(userData.username)}
            </div>
            <div className={`absolute -bottom-1 -right-1 w-4 h-4 bg-[#0f172a] border border-white/10 rounded-full flex items-center justify-center shadow-lg transition-transform duration-300 ${isProfileOpen ? 'rotate-180' : ''}`}>
              <ChevronDown size={10} className={isProfileOpen ? 'text-indigo-400' : 'text-gray-400'} />
            </div>
          </button>

          {/* Profile Dropdown */}
          <AnimatePresence>
            {isProfileOpen && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 10 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
                className="absolute right-0 top-full mt-4 w-72 bg-[#0f172a] rounded-3xl shadow-2xl shadow-black/50 border border-white/10 p-2 z-[60]"
              >
                {/* User Info Section */}
                <div className="p-4 mb-2">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-12 h-12 rounded-2xl bg-indigo-600 border border-white/10 flex items-center justify-center text-xl font-black text-white">
                      {getInitials(userData.username)}
                    </div>
                    <div>
                      <p className="font-black text-white capitalize">{userData.username}</p>
                      <span className="px-2 py-0.5 bg-indigo-500/20 text-indigo-300 text-[10px] font-black rounded-lg uppercase tracking-tight">{userData.role}</span>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs font-semibold text-gray-400">
                      <Mail size={12} className="text-gray-500" />
                      {userData.email}
                    </div>
                    <div className="flex items-center gap-2 text-xs font-semibold text-gray-400">
                      <ShieldCheck size={12} className="text-gray-500" />
                      {userData.access}
                    </div>
                  </div>
                </div>

                <div className="h-px bg-white/5 mx-2 mb-2" />

                {/* Actions Section */}
                <div className="p-1 space-y-1">
                  <p className="px-3 py-2 text-[10px] font-bold text-gray-500 uppercase tracking-widest">Account Actions</p>
                  <Link
                    to="/settings"
                    onClick={() => setIsProfileOpen(false)}
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-2xl text-sm font-bold text-gray-300 hover:bg-white/5 hover:text-white transition-all group"
                  >
                    <div className="w-8 h-8 rounded-xl bg-white/5 flex items-center justify-center group-hover:bg-indigo-500/20 transition-colors">
                      <Settings size={16} />
                    </div>
                    Change Details
                  </Link>
                </div>

                <div className="h-px bg-white/5 mx-2 my-2" />

                {/* Logout Button */}
                <div className="p-1">
                  <button
                    onClick={() => {
                      setIsProfileOpen(false);
                      onLogout();
                    }}
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-2xl text-sm font-bold text-red-500 hover:bg-red-500/10 transition-all group"
                  >
                    <div className="w-8 h-8 rounded-xl bg-red-500/10 flex items-center justify-center group-hover:bg-red-500/20 transition-colors">
                      <LogOut size={16} />
                    </div>
                    Logout Account
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </header>
  );
}
