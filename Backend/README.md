# Multimodal Post-Disaster Sentiment Analysis Backend

A resilient, service-oriented backend for processing multilingual data for disaster intelligence.

## 🚀 Quick Start

The server is running! To restart it in the future:
```powershell
.\venv311\Scripts\Activate.ps1
python run.py
```

## 📚 Documentation

Detailed documentation is available in the `docs/` folder:

- **[Success & Overview](docs/SUCCESS.md)** - What's working and how to test
- **[API Endpoints](docs/API_ENDPOINTS.md)** - Full API reference
- **[Installation Guide](docs/SETUP_PYTHON_311.md)** - Setup instructions
- **[Project Walkthrough](docs/walkthrough.md)** - Architecture implementation details

## 🛠️ Architecture

- **Services**: `app/services/` (Preprocessing, Translation, Sentiment, Event, Location)
- **API Routes**: `app/routes/`
- **Models**: `app/models/`
- **Database**: MongoDB

## ✅ Features

- **Multilingual Support**: 23+ languages (auto-translated)
- **Sentiment Analysis**: VADER (Social Media optimized)
- **Event Detection**: Flood, Fire, Earthquake, Landslide, Terror
- **Location Extraction**: spaCy NER (City, State, Country)
- **Dashboard**: Real-time analytics APIs
