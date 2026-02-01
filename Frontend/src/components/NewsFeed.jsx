import { useState, useEffect, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Search,
    Globe,
    Trophy,
    Film,
    Cpu,
    TrendingUp,
    Clock,
    ExternalLink,
    ChevronRight,
    ChevronLeft,
    ChevronDown,
    Newspaper,
    Loader2,
    AlertCircle,
    RefreshCw,
    Filter,
    X,
    MapPin,
    Languages
} from 'lucide-react';
import { api } from '../services/api';
import ArticleModal from './ArticleModal';

const CATEGORIES = [
    { id: 'all', label: 'All News', icon: <Newspaper size={16} /> },
    { id: 'sports', label: 'Sports', icon: <Trophy size={16} /> },
    { id: 'entertainment', label: 'Entertainment', icon: <Film size={16} /> },
    { id: 'technology', label: 'Technology', icon: <Cpu size={16} /> },
    { id: 'disaster', label: 'Disaster', icon: <AlertCircle size={16} /> },
    { id: 'terror', label: 'Terror', icon: <TrendingUp size={16} /> },
];

const HIERARCHICAL_FILTERS = {
    continents: [
        { code: 'all', name: 'All Continents', icon: '🌍' },
        { code: 'asia', name: 'Asia', icon: '🌏' },
        { code: 'europe', name: 'Europe', icon: '🇪🇺' },
        { code: 'americas', name: 'Americas', icon: '🌎' },
        { code: 'global', name: 'Global', icon: '🌐' },
    ],
    countries: {
        all: [
            { code: 'all', name: 'All Countries' },
            { code: 'india', name: 'India' },
            { code: 'china', name: 'China' },
            { code: 'netherlands', name: 'Netherlands' },
            { code: 'indonesia', name: 'Indonesia' },
            { code: 'middle_east', name: 'Middle East' },
            { code: 'europe', name: 'Europe' },
            { code: 'americas', name: 'Americas' },
            { code: 'global', name: 'Global' },
        ],
        asia: [
            { code: 'all', name: 'All countries in Asia' },
            { code: 'india', name: 'India' },
            { code: 'china', name: 'China' },
            { code: 'indonesia', name: 'Indonesia' },
            { code: 'middle_east', name: 'Middle East' },
        ],
        europe: [
            { code: 'all', name: 'All countries in Europe' },
            { code: 'netherlands', name: 'Netherlands' },
            { code: 'europe', name: 'Other Europe' },
        ],
        americas: [
            { code: 'all', name: 'All countries in Americas' },
            { code: 'americas', name: 'Americas (Region)' },
        ],
        global: [
            { code: 'all', name: 'All Global Sources' },
            { code: 'global', name: 'Global' },
        ],
    },
    languages: {
        all: [
            { code: 'all', name: 'All Languages' },
            { code: 'en', name: 'English' },
            { code: 'hi', name: 'Hindi (हिन्दी)' },
            { code: 'zh', name: 'Chinese (中文)' },
            { code: 'ar', name: 'Arabic (العربية)' },
            { code: 'fr', name: 'French (Français)' },
            { code: 'es', name: 'Spanish (Español)' },
            { code: 'nl', name: 'Dutch (Nederlands)' },
            { code: 'id', name: 'Indonesian (Bahasa)' },
        ],
        india: [
            { code: 'all', name: 'All Languages (India)' },
            { code: 'en', name: 'English' },
            { code: 'hi', name: 'Hindi (हिन्दी)' },
        ],
        china: [
            { code: 'all', name: 'All Languages (China)' },
            { code: 'zh', name: 'Chinese (中文)' },
            { code: 'en', name: 'English' },
        ],
        indonesia: [
            { code: 'all', name: 'All Languages (Indonesia)' },
            { code: 'id', name: 'Indonesian (Bahasa)' },
            { code: 'en', name: 'English' },
        ],
        netherlands: [
            { code: 'all', name: 'All Languages (Netherlands)' },
            { code: 'nl', name: 'Dutch (Nederlands)' },
            { code: 'en', name: 'English' },
        ],
        middle_east: [
            { code: 'all', name: 'All Languages (Middle East)' },
            { code: 'ar', name: 'Arabic (العربية)' },
            { code: 'en', name: 'English' },
        ],
    },
    sources: {
        all: [
            { code: 'all', name: 'All Sources' },
            { code: 'BBC India (English)', name: 'BBC India (English)' },
            { code: 'BBC Hindi', name: 'BBC Hindi' },
            { code: 'BBC Chinese', name: 'BBC Chinese' },
            { code: 'BBC Arabic', name: 'BBC Arabic' },
            { code: 'BBC Middle East (English)', name: 'BBC Middle East' },
            { code: 'BBC Afrique (French)', name: 'BBC Afrique' },
            { code: 'BBC Europe (English)', name: 'BBC Europe' },
            { code: 'BBC Mundo', name: 'BBC Mundo (Spanish)' },
            { code: 'BBC Americas (English)', name: 'BBC Americas' },
            { code: 'BBC Indonesia', name: 'BBC Indonesia' },
            { code: 'BBC World News (English)', name: 'BBC World News' },
        ],
        hi: [
            { code: 'all', name: 'All Hindi Sources' },
            { code: 'BBC Hindi', name: 'BBC India (Hindi)' },
        ],
        zh: [
            { code: 'all', name: 'All Chinese Sources' },
            { code: 'BBC Chinese', name: 'BBC Chinese' },
        ],
        en: {
            india: [
                { code: 'all', name: 'All English Sources (India)' },
                { code: 'BBC India (English)', name: 'BBC India (English)' },
            ],
            europe: [
                { code: 'all', name: 'All English Sources (Europe)' },
                { code: 'BBC Europe (English)', name: 'BBC Europe' },
            ],
            americas: [
                { code: 'all', name: 'All English Sources (Americas)' },
                { code: 'BBC Americas (English)', name: 'BBC Americas' },
            ],
            global: [
                { code: 'all', name: 'All English Sources (Global)' },
                { code: 'BBC World News (English)', name: 'BBC World News' },
            ],
            'middle_east': [
                { code: 'all', name: 'All English Sources (Middle East)' },
                { code: 'BBC Middle East (English)', name: 'BBC Middle East' },
            ]
        }
    }
};

const REVERSE_LOOKUP = {
    countries: {
        india: 'asia',
        china: 'asia',
        indonesia: 'asia',
        middle_east: 'asia',
        netherlands: 'europe',
        europe: 'europe',
        americas: 'americas',
        global: 'global'
    },
    languages: {
        hi: { country: 'india', continent: 'asia' },
        zh: { country: 'china', continent: 'asia' },
        ar: { country: 'middle_east', continent: 'asia' },
        nl: { country: 'netherlands', continent: 'europe' },
        id: { country: 'indonesia', continent: 'asia' },
    },
    sources: {
        'BBC Hindi': { language: 'hi', country: 'india', continent: 'asia' },
        'BBC Chinese': { language: 'zh', country: 'china', continent: 'asia' },
        'BBC Arabic': { language: 'ar', country: 'middle_east', continent: 'asia' },
        'BBC India (English)': { language: 'en', country: 'india', continent: 'asia' },
        'BBC Middle East (English)': { language: 'en', country: 'middle_east', continent: 'asia' },
        'BBC Afrique (French)': { language: 'fr', country: 'all', continent: 'all' },
        'BBC Europe (English)': { language: 'en', country: 'europe', continent: 'europe' },
        'BBC Mundo': { language: 'es', country: 'americas', continent: 'americas' },
        'BBC Americas (English)': { language: 'en', country: 'americas', continent: 'americas' },
        'BBC Indonesia': { language: 'id', country: 'indonesia', continent: 'asia' },
        'BBC World News (English)': { language: 'en', country: 'global', continent: 'global' }
    }
};


export default function NewsFeed() {
    const getDisplayValue = (prop, lang = 'en') => {
        if (typeof prop === 'string') return prop;
        if (typeof prop === 'object' && prop !== null) {
            let value = prop;
            if ('value' in prop) value = prop.value;
            else if (lang in prop) value = prop[lang];
            else if (Object.keys(prop).length > 0) value = prop[Object.keys(prop)[0]];
            
            // Handle nested objects (e.g., if value is still an object)
            if (typeof value === 'object' && value !== null) {
                if (lang in value) return value[lang];
                if (Object.keys(value).length > 0) return value[Object.keys(value)[0]];
                return JSON.stringify(value); // Fallback to stringify
            }
            
            return typeof value === 'string' ? value : String(value);
        }
        return String(prop);
    };
    const navigate = useNavigate();
    const [searchQuery, setSearchQuery] = useState('');
    const [activeCategory, setActiveCategory] = useState('all');
    const [news, setNews] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [pagination, setPagination] = useState({
        currentPage: 1,
        itemsPerPage: 25,
        totalLoaded: 0,
        hasMore: false,
        cursor: null,
        cursorHistory: [] // Track cursors for backward navigation
    });
    const fetchingRef = useRef(false);
    const hasFetchedRef = useRef(false);

    // Filter states
    const [showFilters, setShowFilters] = useState(false);
    const [filters, setFilters] = useState({
        continent: 'all',
        country: 'all',
        language: 'all',
        source: 'all'
    });
    // Temporary filter state (before Apply is clicked)
    const [tempFilters, setTempFilters] = useState({
        continent: 'all',
        country: 'all',
        language: 'all',
        source: 'all'
    });

    const [isSearching, setIsSearching] = useState(false);
    const [selectedArticle, setSelectedArticle] = useState(null);
    const [isModalOpen, setIsModalOpen] = useState(false);

    const handleArticleClick = (article) => {
        setSelectedArticle(article);
        setIsModalOpen(true);
    };

    const handleSearch = async (query) => {
        if (!query.trim()) {
            setIsSearching(false);
            fetchNews(null);
            return;
        }

        setLoading(true);
        setIsSearching(true);
        setError(null);
        try {
            const response = await api.intelliSearch(query);
            if (response.status === 'success') {
                setNews(response.results || []);
                setPagination(prev => ({
                    ...prev,
                    currentPage: 1,
                    hasMore: false,
                    totalLoaded: response.count || 0
                }));
            }
        } catch (err) {
            console.error('IntelliSearch failed:', err);
            setError('Search failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    // Fetch news from backend
    const fetchNews = async (cursor = null, isNext = true, overrideLimit = null) => {
        if (isSearching) return; // Don't fetch regular news while searching
        // Prevent duplicate calls
        if (fetchingRef.current) {
            console.log('Fetch already in progress, skipping...');
            return;
        }

        fetchingRef.current = true;
        setLoading(true);
        setError(null);

        // Clear news when paginating to avoid showing stale content
        if (cursor !== null) {
            setNews([]);
        }

        try {
            const params = {
                limit: overrideLimit || pagination.itemsPerPage,
                continent: filters.continent !== 'all' ? filters.continent : undefined,
                country: filters.country !== 'all' ? filters.country : undefined,
                language: filters.language !== 'all' ? filters.language : undefined,
                source: filters.source !== 'all' ? filters.source : undefined
            };

            // Add category filter if not 'all'
            if (activeCategory !== 'all') {
                params.category = activeCategory;
            }


            // Add cursor for pagination
            if (cursor) {
                params.cursor = cursor;
            }

            const response = await api.listNews(params);

            if (response.status === 'success') {
                const fetchedNews = response.articles || [];
                const blendedItems = fetchedNews;

                setNews(blendedItems);

                // Update pagination with cursor tracking
                setPagination(prev => {
                    const nextItems = response.articles?.length || 0;
                    const isInitialFetch = cursor === null;
                    const total = response.total || (isInitialFetch ? nextItems : prev.totalLoaded + nextItems);

                    return {
                        ...prev,
                        cursor: response.next_cursor || null,
                        hasMore: response.has_more || false,
                        totalLoaded: total,
                        currentPage: isInitialFetch ? 1 : (isNext ? prev.currentPage + 1 : Math.max(1, prev.currentPage - 1)),
                        cursorHistory: isNext
                            ? (isInitialFetch ? [] : [...prev.cursorHistory, cursor])
                            : prev.cursorHistory.slice(0, -1)
                    };
                });
            }
        } catch (err) {
            console.error('Failed to fetch news:', err);
            setError(err.message || 'Failed to load news');
            setNews([]);
        } finally {
            setLoading(false);
            fetchingRef.current = false;
        }
    };

    // Fetch news on component mount and when category changes
    useEffect(() => {
        // Only fetch once on mount
        if (!hasFetchedRef.current) {
            hasFetchedRef.current = true;
            fetchNews(null);
        }
    }, []);

    // Fetch when category changes
    useEffect(() => {
        // Skip initial render
        if (hasFetchedRef.current) {
            // Reset pagination when category changes
            setPagination(prev => ({
                ...prev,
                currentPage: 1,
                totalLoaded: 0,
                cursorHistory: [],
                cursor: null
            }));
            fetchNews(null, true);
        }
    }, [activeCategory]);

    // Fetch when filters change
    useEffect(() => {
        // Skip initial render
        if (hasFetchedRef.current) {
            // Reset pagination when filters change
            setPagination(prev => ({
                ...prev,
                currentPage: 1,
                totalLoaded: 0,
                cursorHistory: [],
                cursor: null
            }));
            fetchNews(null, true);
        }
    }, [filters]);

    // Logic for filtered news (search is now handled by backend)
    const filteredNews = news;

    // Format date/time
    const formatTime = (dateString) => {
        if (!dateString) return 'Recently';

        try {
            const date = new Date(dateString);
            const now = new Date();
            const diffMs = now - date;
            const diffMins = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMins / 60);
            const diffDays = Math.floor(diffHours / 24);

            if (diffMins < 60) return `${diffMins} minutes ago`;
            if (diffHours < 24) return `${diffHours} hours ago`;
            if (diffDays < 7) return `${diffDays} days ago`;

            return date.toLocaleDateString();
        } catch {
            return 'Recently';
        }
    };

    // Get image URL with fallback
    const getImageUrl = (article) => {
        // Use image_url from API if available
        if (article.image_url) {
            return article.image_url;
        }

        // Fallback to category-based placeholder
        const images = {
            world: 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&q=80&w=800',
            sports: 'https://images.unsplash.com/photo-1508098682722-e99c43a406b2?auto=format&fit=crop&q=80&w=800',
            technology: 'https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&q=80&w=800',
            entertainment: 'https://images.unsplash.com/photo-1485846234645-a62644f84728?auto=format&fit=crop&q=80&w=800',
            disaster: 'https://images.unsplash.com/photo-1527031086912-b1633cf44ca3?auto=format&fit=crop&q=80&w=800',
            terror: 'https://images.unsplash.com/photo-1506146332389-18140dc7b2fb?auto=format&fit=crop&q=80&w=800',
        };
        return images[article.category] || 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&q=80&w=800';
    };

    // Pagination handlers
    const handleNextPage = () => {
        if (pagination.hasMore && pagination.cursor) {
            fetchNews(pagination.cursor, true);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    };

    const handlePreviousPage = () => {
        if (pagination.currentPage > 1) {
            const previousCursor = pagination.cursorHistory[pagination.cursorHistory.length - 2] || null;
            fetchNews(previousCursor, false);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    };

    const handleItemsPerPageChange = (newLimit) => {
        setPagination(prev => ({
            ...prev,
            itemsPerPage: newLimit,
            currentPage: 1,
            totalLoaded: 0,
            cursorHistory: []
        }));
        fetchNews(null, true, newLimit);
    };

    const handleRefreshPage = () => {
        setPagination(prev => ({
            ...prev,
            currentPage: 1,
            totalLoaded: 0,
            cursorHistory: []
        }));
        fetchNews(null, true);
    };

    const featuredNews = filteredNews.length > 0 ? filteredNews[0] : null;

    return (
        <div className="space-y-12 pb-20 pt-24">
            {/* Header & Search */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-8">
                <div className="space-y-2">
                    <div className="flex items-center gap-2 mb-2">
                        <span className="px-3 py-1 bg-red-500/10 text-red-400 text-[10px] font-black rounded-full uppercase tracking-widest border border-red-500/20 flex items-center gap-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" /> Live News
                        </span>
                    </div>
                    <h2 className="text-4xl font-black text-white tracking-tight">Real-Time News Feed</h2>
                    <p className="text-gray-400 max-w-lg">Stay updated with the latest headlines from around the globe, curated just for you.</p>
                </div>

                <div className="flex items-center gap-3">
                    <div className="relative group w-full md:w-96">
                        <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-indigo-400 transition-colors" size={20} />
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => {
                                const val = e.target.value;
                                setSearchQuery(val);
                                if (!val.trim()) handleSearch(''); // Reset when cleared
                            }}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') handleSearch(searchQuery);
                            }}
                            placeholder="Search news, topics..."
                            className="w-full pl-14 pr-6 py-4 bg-white/5 border border-white/10 rounded-2xl outline-none focus:ring-4 focus:ring-indigo-500/10 transition-all shadow-sm text-white placeholder-gray-500"
                        />
                    </div>

                    <button
                        onClick={() => handleSearch(searchQuery)}
                        disabled={loading}
                        className="p-4 bg-white/5 border border-white/10 rounded-2xl hover:bg-white/10 transition-all disabled:opacity-50"
                        title="IntelliSearch"
                    >
                        <Search size={20} className={`text-indigo-400 ${loading ? 'animate-spin' : ''}`} />
                    </button>
                </div>
            </div>

            {/* Category Tabs */}
            <div className="flex flex-wrap items-center gap-3 pb-2">
                <div className="flex flex-wrap items-center gap-2 flex-1">
                    {CATEGORIES.map((cat) => (
                        <button
                            key={cat.id}
                            onClick={() => setActiveCategory(cat.id)}
                            disabled={loading}
                            className={`flex items-center gap-2 px-6 py-3 rounded-xl font-bold transition-all whitespace-nowrap border ${activeCategory === cat.id
                                ? 'bg-indigo-600 border-indigo-500 text-white shadow-lg shadow-indigo-500/20 scale-105'
                                : 'bg-white/5 border-white/10 text-gray-400 hover:border-indigo-500/30 hover:text-white'
                                } disabled:opacity-50`}
                        >
                            {cat.icon}
                            {cat.label}
                        </button>
                    ))}
                </div>

                {/* Filter Toggle Button */}
                <button
                    onClick={() => setShowFilters(!showFilters)}
                    className={`flex items-center gap-2 px-6 py-3 rounded-xl font-bold transition-all whitespace-nowrap border ${showFilters || filters.continent !== 'all' || filters.country !== 'all' || filters.language !== 'all' || filters.source !== 'all'
                        ? 'bg-indigo-500/20 border-indigo-500 text-indigo-300'
                        : 'bg-white/5 border-white/10 text-gray-400 hover:border-white/20'
                        }`}
                >
                    <Filter size={16} />
                    Filters
                    {(filters.continent !== 'all' || filters.country !== 'all' || filters.language !== 'all' || filters.source !== 'all') && (
                        <span className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse" />
                    )}
                </button>
            </div>

            {/* Filter Popup Modal */}
            <AnimatePresence>
                {showFilters && (
                    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 md:p-12 overflow-y-auto">
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setShowFilters(false)}
                            className="fixed inset-0 bg-black/80 backdrop-blur-xl transition-all"
                        />
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95, y: 20 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.95, y: 20 }}
                            className="relative w-full max-w-4xl bg-[#0f172a] border border-white/10 rounded-[40px] shadow-2xl overflow-hidden p-8 md:p-12 z-[101] m-auto"
                        >
                            <div className="flex items-center justify-between mb-8">
                                <div className="space-y-1">
                                    <h3 className="text-2xl font-black text-white flex items-center gap-3">
                                        <Filter size={24} className="text-indigo-400" />
                                        Advanced News Analysis Filters
                                    </h3>
                                    <p className="text-gray-400 text-sm font-medium">Fine-tune your news feed with precise geographical and linguistic controls.</p>
                                </div>
                                <button
                                    onClick={() => setShowFilters(false)}
                                    className="p-3 bg-white/5 hover:bg-white/10 rounded-2xl text-gray-400 hover:text-white transition-all border border-white/10"
                                >
                                    <X size={20} />
                                </button>
                            </div>

                            {/* Hierarchical Filter Logic Content */}
                            {(() => {
                                const getAvailableCountries = () => HIERARCHICAL_FILTERS.countries[tempFilters.continent] || HIERARCHICAL_FILTERS.countries.all;
                                const getAvailableLanguages = () => {
                                    if (tempFilters.country !== 'all') return HIERARCHICAL_FILTERS.languages[tempFilters.country] || HIERARCHICAL_FILTERS.languages.all;
                                    if (tempFilters.continent !== 'all') {
                                        const countriesInContinent = HIERARCHICAL_FILTERS.countries[tempFilters.continent] || [];
                                        const languages = new Set(['all']);
                                        countriesInContinent.forEach(c => { if (c.code !== 'all') (HIERARCHICAL_FILTERS.languages[c.code] || []).forEach(l => languages.add(l.code)); });
                                        return HIERARCHICAL_FILTERS.languages.all.filter(l => languages.has(l.code));
                                    }
                                    return HIERARCHICAL_FILTERS.languages.all;
                                };
                                const getAvailableSources = () => {
                                    let baseSources = HIERARCHICAL_FILTERS.sources.all;
                                    if (tempFilters.language !== 'all') {
                                        const langSources = HIERARCHICAL_FILTERS.sources[tempFilters.language];
                                        if (tempFilters.language === 'en' && typeof langSources === 'object' && !Array.isArray(langSources)) {
                                            baseSources = langSources[tempFilters.country] || langSources.global || HIERARCHICAL_FILTERS.sources.all;
                                        } else { baseSources = langSources || HIERARCHICAL_FILTERS.sources.all; }
                                    } else if (tempFilters.country !== 'all') {
                                        const countryLangs = HIERARCHICAL_FILTERS.languages[tempFilters.country] || [];
                                        const sources = new Set(['all']);
                                        countryLangs.forEach(l => { if (l.code !== 'all') { const langSources = HIERARCHICAL_FILTERS.sources[l.code]; if (l.code === 'en' && typeof langSources === 'object') { (langSources[tempFilters.country] || []).forEach(s => sources.add(s.code)); } else (langSources || []).forEach(s => sources.add(s.code)); } });
                                        baseSources = HIERARCHICAL_FILTERS.sources.all.filter(s => sources.has(s.code));
                                    }
                                    return baseSources;
                                };

                                const availableCountries = getAvailableCountries();
                                const availableLanguages = getAvailableLanguages();
                                const availableSources = getAvailableSources();

                                return (
                                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                                        <div className="space-y-2">
                                            <label className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] ml-1">Continent</label>
                                            <div className="relative group">
                                                <Globe className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-indigo-400" size={18} />
                                                <select
                                                    value={tempFilters.continent}
                                                    onChange={(e) => {
                                                        const continent = e.target.value;
                                                        setTempFilters({
                                                            ...tempFilters,
                                                            continent,
                                                            // If changing continent, reset children if they don't belong
                                                            country: 'all',
                                                            language: 'all',
                                                            source: 'all'
                                                        });
                                                    }}
                                                    className="w-full pl-12 pr-4 py-4 bg-white/5 border border-white/10 rounded-2xl font-bold text-white outline-none focus:ring-4 focus:ring-indigo-500/10 transition-all appearance-none"
                                                >
                                                    {HIERARCHICAL_FILTERS.continents.map((c) => <option key={c.code} value={c.code} className="bg-[#1e293b]">{c.icon} {c.name}</option>)}
                                                </select>
                                                <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" size={16} />
                                            </div>
                                        </div>

                                        <div className="space-y-2">
                                            <label className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] ml-1">Country/Region</label>
                                            <div className="relative group">
                                                <MapPin className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-indigo-400" size={18} />
                                                <select
                                                    value={tempFilters.country}
                                                    onChange={(e) => {
                                                        const country = e.target.value;
                                                        let updates = { country, language: 'all', source: 'all' };

                                                        if (country !== 'all') {
                                                            const continent = REVERSE_LOOKUP.countries[country];
                                                            if (continent) updates.continent = continent;
                                                        }

                                                        setTempFilters({ ...tempFilters, ...updates });
                                                    }}
                                                    className="w-full pl-12 pr-4 py-4 bg-white/5 border border-white/10 rounded-2xl font-bold text-white outline-none focus:ring-4 focus:ring-indigo-500/10 transition-all appearance-none"
                                                >
                                                    {availableCountries.map((c) => <option key={c.code} value={c.code} className="bg-[#1e293b]">{c.name}</option>)}
                                                </select>
                                                <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" size={16} />
                                            </div>
                                        </div>

                                        <div className="space-y-2">
                                            <label className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] ml-1">Language</label>
                                            <div className="relative group">
                                                <Languages className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-indigo-400" size={18} />
                                                <select
                                                    value={tempFilters.language}
                                                    onChange={(e) => {
                                                        const lang = e.target.value;
                                                        let updates = { language: lang, source: 'all' };

                                                        if (lang !== 'all' && REVERSE_LOOKUP.languages[lang]) {
                                                            const { country, continent } = REVERSE_LOOKUP.languages[lang];
                                                            updates.country = country;
                                                            updates.continent = continent;
                                                        }

                                                        setTempFilters({ ...tempFilters, ...updates });
                                                    }}
                                                    className="w-full pl-12 pr-4 py-4 bg-white/5 border border-white/10 rounded-2xl font-bold text-white outline-none focus:ring-4 focus:ring-indigo-500/10 transition-all appearance-none"
                                                >
                                                    {availableLanguages.map((l) => <option key={l.code} value={l.code} className="bg-[#1e293b]">{l.name}</option>)}
                                                </select>
                                                <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" size={16} />
                                            </div>
                                        </div>

                                        <div className="space-y-2 lg:col-span-2">
                                            <label className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] ml-1">News Source</label>
                                            <div className="relative group">
                                                <Newspaper className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-indigo-400" size={18} />
                                                <select
                                                    value={tempFilters.source}
                                                    onChange={(e) => {
                                                        const source = e.target.value;
                                                        let updates = { source };

                                                        if (source !== 'all' && REVERSE_LOOKUP.sources[source]) {
                                                            const metadata = REVERSE_LOOKUP.sources[source];
                                                            updates = { ...updates, ...metadata };
                                                        }

                                                        setTempFilters({ ...tempFilters, ...updates });
                                                    }}
                                                    className="w-full pl-12 pr-4 py-4 bg-white/5 border border-white/10 rounded-2xl font-bold text-white outline-none focus:ring-4 focus:ring-indigo-500/10 transition-all appearance-none"
                                                >
                                                    {availableSources.map((s) => <option key={s.code} value={s.code} className="bg-[#1e293b]">{s.name}</option>)}
                                                </select>
                                                <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" size={16} />
                                            </div>
                                        </div>

                                    </div>
                                );
                            })()}

                            <div className="flex flex-col sm:flex-row items-center gap-4 mt-12 pt-8 border-t border-white/10">
                                <button
                                    onClick={() => {
                                        const cleared = { continent: 'all', country: 'all', language: 'all', source: 'all' };
                                        setTempFilters(cleared);
                                        setFilters(cleared);
                                    }}
                                    className="w-full sm:w-auto px-8 py-4 text-gray-400 font-bold hover:text-white transition-colors"
                                >
                                    Reset to Default
                                </button>
                                <div className="flex-1" />
                                <button
                                    onClick={() => setShowFilters(false)}
                                    className="w-full sm:w-auto px-8 py-4 bg-white/5 text-white rounded-2xl font-black border border-white/10 hover:bg-white/10 transition-all"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={() => {
                                        setFilters(tempFilters);
                                        setShowFilters(false);
                                    }}
                                    className="w-full sm:w-auto px-10 py-4 bg-indigo-600 text-white rounded-2xl font-black shadow-xl shadow-indigo-500/20 hover:bg-indigo-500 hover:scale-[1.02] transition-all flex items-center justify-center gap-3"
                                >
                                    <Filter size={20} />
                                    Apply Changes
                                </button>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>

            {/* Error Message */}
            {error && (
                <div className="p-6 bg-red-500/10 text-red-400 rounded-2xl flex items-center gap-3 font-bold animate-fade-in border border-red-500/20">
                    <AlertCircle size={20} />
                    <span>{error}</span>
                    <button
                        onClick={() => fetchNews(null)}
                        className="ml-auto px-4 py-2 bg-red-500 text-white rounded-xl hover:bg-red-600 transition-colors"
                    >
                        Retry
                    </button>
                </div>
            )}

            {/* Loading State */}
            {loading && news.length === 0 && (
                <div className="py-20 text-center">
                    <Loader2 className="w-12 h-12 animate-spin text-indigo-500 mx-auto mb-4" />
                    <p className="text-gray-400 font-bold">Loading news...</p>
                </div>
            )}

            {/* Breaking News Hero */}
            {featuredNews && !loading && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    onClick={() => handleArticleClick(featuredNews)}
                    className="relative h-[450px] rounded-[40px] overflow-hidden group cursor-pointer shadow-2xl shadow-indigo-500/10 mb-12"
                >
                    <img
                        src={getImageUrl(featuredNews)}
                        alt={featuredNews.title}
                        className="absolute inset-0 w-full h-full object-cover group-hover:scale-110 transition-transform duration-1000"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent" />

                    <div className="absolute bottom-0 left-0 p-12 w-full max-w-4xl space-y-6">
                        <div className="flex items-center gap-3">
                            <span className="text-white/70 text-sm font-bold flex items-center gap-2">
                                <Clock size={16} /> {formatTime(featuredNews.published_date)}
                            </span>
                        </div>
                        <h3 className="text-5xl font-black text-white leading-tight">{getDisplayValue(featuredNews.title)}</h3>
                        <p className="text-white/80 text-lg leading-relaxed">{getDisplayValue(featuredNews.summary) || 'Click to read the full article and view AI-powered analysis.'}</p>
                        <button className="bg-white text-black px-8 py-4 rounded-2xl font-black flex items-center gap-3 hover:bg-gray-100 transition-colors shadow-xl">
                            Read Full Article <ExternalLink size={18} />
                        </button>
                    </div>
                </motion.div>
            )}

            {/* News Grid */}
            {!loading && filteredNews.length > 0 && (
                <>
                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
                        <AnimatePresence mode="popLayout">
                            {filteredNews.slice(featuredNews ? 1 : 0).map((article, i) => (
                                <motion.div
                                    layout
                                    key={article._id || article.id}
                                    initial={{ opacity: 0, scale: 0.9 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    exit={{ opacity: 0, scale: 0.9 }}
                                    transition={{ duration: 0.3, delay: i * 0.05 }}
                                    onClick={() => handleArticleClick(article)}
                                    className="bg-white/5 backdrop-blur-md rounded-[32px] border border-white/10 overflow-hidden group hover:bg-white/10 hover:border-white/20 transition-all flex flex-col cursor-pointer"
                                >
                                    <div className="relative h-56 overflow-hidden">
                                        <img
                                            src={getImageUrl(article)}
                                            alt={article.title}
                                            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
                                        />
                                        <span className="absolute top-4 left-4 bg-indigo-600/90 backdrop-blur-md px-3 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest text-white border border-white/20">
                                            {getDisplayValue(article.category) || 'News'}
                                        </span>
                                    </div>

                                    <div className="p-8 flex-1 flex flex-col">
                                        <div className="flex items-center gap-3 text-gray-400 text-xs font-bold mb-4">
                                            <span className="hover:text-indigo-400 transition-colors cursor-pointer">{getDisplayValue(article.source) || 'Unknown Source'}</span>
                                            <span className="w-1 h-1 rounded-full bg-white/20" />
                                            <span>{formatTime(article.published_date)}</span>
                                        </div>

                                        <h4 className="text-xl font-bold text-white mb-4 leading-snug group-hover:text-indigo-400 transition-colors line-clamp-2">
                                            {getDisplayValue(article.title)}
                                        </h4>

                                        <p className="text-gray-400 text-sm leading-relaxed mb-6 line-clamp-3 font-medium">
                                            {getDisplayValue(article.summary) || 'Click to read the full article and view detailed analysis.'}
                                        </p>

                                        <div className="mt-auto pt-6 border-t border-white/5 flex items-center justify-between group/btn">
                                            <span className="text-sm font-black text-white group-hover/btn:translate-x-1 transition-transform flex items-center gap-2">
                                                Analyze Article <ChevronRight size={16} className="text-indigo-500" />
                                            </span>
                                            <div className="p-2 bg-white/5 rounded-xl text-gray-400 group-hover:bg-indigo-500 group-hover:text-white transition-all">
                                                <ExternalLink size={16} />
                                            </div>
                                        </div>
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    </div>
                </>
            )}

            {/* Empty State */}
            {!loading && filteredNews.length === 0 && !error && (
                <div className="py-24 text-center">
                    <div className="w-24 h-24 bg-white/5 rounded-[32px] border border-white/10 flex items-center justify-center mx-auto mb-8 text-indigo-400 shadow-xl">
                        <Search size={40} />
                    </div>
                    <h3 className="text-3xl font-black text-white mb-3">No news found</h3>
                    <p className="text-gray-400 font-medium max-w-sm mx-auto">Try adjusting your search query or refine your advanced filters to explore more articles.</p>
                </div>
            )}

            {/* Article Detail Modal */}
            <ArticleModal 
                isOpen={isModalOpen}
                article={selectedArticle}
                onClose={() => setIsModalOpen(false)}
            />
        </div>
    );
}
