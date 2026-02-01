import { useState } from 'react'
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom'
import { GoogleOAuthProvider } from '@react-oauth/google'
import Header from './components/Header'
import Hero from './components/Hero'
import AnalysisCard from './components/AnalysisCard'
import Home from './components/Home'
import Analyze from './components/Analyze'
import NewsFeed from './components/NewsFeed'
import ArticleDetail from './pages/ArticleDetail'
import About from './components/About'
import Settings from './components/Settings'
import Login from './components/Login'
import Register from './components/Register'
import InteractiveBackground from './components/InteractiveBackground'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'));
  const [authPage, setAuthPage] = useState('login'); // 'login' or 'register'
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogin = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setIsAuthenticated(false);
    setAuthPage('login');
  };

  return (
    <GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID}>
      {!isAuthenticated ? (
        authPage === 'login' ? (
          <Login onLogin={handleLogin} onSwitchToRegister={() => setAuthPage('register')} />
        ) : (
          <Register onRegister={handleLogin} onSwitchToLogin={() => setAuthPage('login')} />
        )
      ) : (
        <div className="min-h-screen flex flex-col relative overflow-hidden text-white selection:bg-indigo-500/30 selection:text-indigo-200">
          <InteractiveBackground />
          <Header onLogout={handleLogout} />

          <main className="flex-1 relative z-10 w-full">
            <Routes>
              <Route path="/" element={
                <div className="container mx-auto max-w-7xl pt-8 pb-20">
                  <Home onGetStarted={() => navigate('/analyze')} />
                </div>
              } />

              <Route path="/analyze" element={<Analyze />} />

              <Route path="/news" element={
                <div className="container mx-auto max-w-7xl px-4 pb-8">
                  <NewsFeed />
                </div>
              } />

              <Route path="/article/:id" element={<ArticleDetail />} />

              <Route path="/about" element={<About />} />

              <Route path="/settings" element={<Settings />} />

              {/* Redirect unknown routes to home */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>

          {!location.pathname.startsWith('/analyze') && <Footer />}
        </div>
      )}
    </GoogleOAuthProvider>
  )
}

// Footer Component
function Footer() {
  return (
    <footer className="py-12 border-t border-white/10 bg-white/5 backdrop-blur-md relative z-10">
      <div className="container mx-auto px-8 flex flex-col md:flex-row justify-between items-center gap-6">
        <div className="flex items-center gap-2 opacity-80">
          <div className="w-10 h-10 rounded-xl overflow-hidden border border-white/10 shadow-lg shadow-indigo-500/20">
            <img src="/logo.jpeg" alt="InsightPoint" className="w-full h-full object-cover" />
          </div>
          <span className="font-black text-xl tracking-tight text-white">InsightPoint</span>
        </div>
        <p className="text-gray-500 text-sm font-medium">© 2026 InsightPoint AI. All rights reserved.</p>
        <div className="flex gap-8">
          <a href="#" className="text-sm font-bold text-gray-500 hover:text-white transition-colors">Privacy Policy</a>
          <a href="#" className="text-sm font-bold text-gray-500 hover:text-white transition-colors">Terms of Service</a>
        </div>
      </div>
    </footer>
  );
}

export default App
