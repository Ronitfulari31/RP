# 🚀 InsightPoint - AI-Powered News Intelligence Platform

![InsightPoint](public/logo.jpeg)

**InsightPoint** is a cutting-edge news analysis platform that leverages advanced AI and Natural Language Processing to provide real-time news intelligence, sentiment analysis, and document processing capabilities.

## ✨ Features

### 📰 Real-Time News Feed
- **Live News Aggregation**: Curated news from global sources across multiple categories
- **Advanced Filtering**: Hierarchical filtering by continent, country, language, and source
- **Category Navigation**: Browse news by Sports, Entertainment, Technology, Disaster, and Terror
- **Smart Search**: Instant search across all news articles

### 🔍 Document Analysis Suite
- **Multi-Format Upload**: Support for PDF, DOCX, and TXT files
- **Sentiment Analysis**: AI-powered sentiment detection with confidence scores
- **Document Summarization**: Automatic text summarization with reduction metrics
- **Keyword Extraction**: RAKE algorithm-based keyword identification
- **Multi-Language Translation**: Neural machine translation across 9+ languages

### 📊 Analytics Dashboard
- **Sentiment Tracking**: Visualize sentiment distributions and trends
- **Usage Statistics**: Track feature usage and processing metrics
- **Document Management**: Comprehensive document library with analytics

### 👤 User Management
- **Profile Customization**: Editable user profiles with initials-based avatars
- **Security Settings**: Password management and authentication controls
- **Personalized Experience**: Tailored dashboard and preferences

## 🛠️ Tech Stack

### Frontend
- **React 19** - Modern UI library
- **Vite** - Lightning-fast build tool
- **React Router** - Client-side routing
- **Framer Motion** - Smooth animations
- **Tailwind CSS** - Utility-first styling

### UI Components & Icons
- **Lucide React** - Beautiful icon library
- **Recharts** - Data visualization

### Backend Integration
- Custom API service layer for seamless backend communication

## 🚀 Getting Started

### Prerequisites

- **Node.js** (v18 or higher)
- **npm** or **yarn**
- **Google OAuth Credentials** (for authentication)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Frontend_atharv
   ```

2. **Configure Environment Variables**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env and add your Google OAuth Client ID
   # Get your client ID from: https://console.cloud.google.com/apis/credentials
   ```

3. **Install dependencies**
   ```bash
   npm install
   ```

4. **Start the development server**
   ```bash
   npm run dev
   ```

5. **Open your browser**
   Navigate to `http://localhost:5173`

### Building for Production

```bash
npm run build
```

The optimized production build will be available in the `dist` folder.

## 📁 Project Structure

```
Frontend_atharv/
├── public/
│   └── logo.jpeg
├── src/
│   ├── components/
│   │   ├── About.jsx
│   │   ├── Analyze.jsx
│   │   ├── AnalysisCard.jsx
│   │   ├── AnalyticsReports.jsx
│   │   ├── DetailedStats.jsx
│   │   ├── DocumentList.jsx
│   │   ├── Header.jsx
│   │   ├── Home.jsx
│   │   ├── InteractiveBackground.jsx
│   │   ├── KeywordExtraction.jsx
│   │   ├── Login.jsx
│   │   ├── NewsFeed.jsx
│   │   ├── Register.jsx
│   │   ├── SentimentAnalysis.jsx
│   │   ├── Settings.jsx
│   │   ├── Summarization.jsx
│   │   └── Translation.jsx
│   ├── pages/
│   │   └── ArticleDetail.jsx
│   ├── services/
│   │   ├── api.js
│   │   └── demoData.js
│   ├── App.jsx
│   ├── index.css
│   └── main.jsx
├── index.html
├── package.json
├── tailwind.config.js
└── vite.config.js
```

## 🎨 Design Features

- **Dark Glassmorphism Theme**: Modern, elegant UI with frosted glass effects
- **Responsive Design**: Optimized for desktop, tablet, and mobile devices
- **Smooth Animations**: Framer Motion powered transitions
- **Interactive Background**: Dynamic particle effects
- **Consistent Branding**: Unified color scheme and typography

## 🔐 Authentication

- Secure login and registration system
- Token-based authentication
- Protected routes and user sessions

## 📊 Key Components

### Analyze Dashboard
- Collapsible sidebar navigation
- Upload documents or paste text
- Real-time analysis results
- Multi-tab interface for different analysis types

### News Feed
- Live news updates
- Advanced hierarchical filtering
- Category-based browsing
- Article detail views

### Settings
- Profile management
- Security & password controls
- Notification preferences
- Appearance customization

## 🌐 API Integration

The application integrates with a backend API for:
- News aggregation and filtering
- Document upload and processing
- Sentiment analysis
- Text summarization
- Keyword extraction
- Multi-language translation

## 📝 License

© 2026 InsightPoint AI. All rights reserved.

## 👥 Contributing

This is a final year B.Tech project. For any queries or suggestions, please contact the development team.

## 🔗 Links

- **Privacy Policy**: [Link]
- **Terms of Service**: [Link]

---

**Built with ❤️ using React, Vite, and modern web technologies**
