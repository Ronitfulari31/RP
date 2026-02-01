# Pipeline Library & Function Guide

This guide breaks down the core functions in your backend services, explaining *why* they exist ("Motive") and *which* strictly approved library controls them.

---

## 1. Local Translation Service (`translation.py`)

| Function | Motive | Library Used |
| :--- | :--- | :--- |
| **`translate_to_english`** | **The Main Entry Point.** Logic wrapper that decides whether to use NLLB (GPU) or Argos (CPU) based on availability. Handles chunking for long texts. | **Logic Controller** |
| `_translate_with_nllb_v2` | **High-Quality Translation.** Loads the NLLB model on GPU to translate text with maximum accuracy. | **Transformers** (`facebook/nllb-200`) |
| `_translate_with_argos` | **Offline Safety Net.** Translates text using locally installed packages when GPU is unavailable. | **Argos Translate** |
| `_load_nllb_v2` | **Resource Management.** Lazy-loads the heavy 1.2GB NLLB model onto the GPU only when needed. | **Transformers** |

## 2. Sentiment Analysis (`sentiment.py`)

| Function | Motive | Library Used |
| :--- | :--- | :--- |
| **`analyze`** | **The Main Entry Point.** Orchestrates the analysis, prioritizing the RoBERTa model and falling back to BERTweet. | **Logic Controller** |
| `analyze_with_v2_local` | **Nuanced Sentiment.** Uses RoBERTa (specifically trained on tweets) to detect positive/negative/neutral sentiment with high confidence. | **Transformers** (`cardiffnlp/roberta`) |
| `analyze_with_v1_local` | **Fallback Sentiment.** Uses BERTweet as a lighter-weight GPU alternative if RoBERTa fails. | **Transformers** (`bertweet`) |
| `_load_roberta_v2` | **Resource Management.** Loads the RoBERTa model into GPU memory safely. | **Transformers** |

## 3. Named Entity Recognition - NER (`ner.py`)

| Function | Motive | Library Used |
| :--- | :--- | :--- |
| **`extract_entities`** | **The Main Entry Point.** Tries to get entities from GLiNER first, then falls back to SpaCy if GLiNER fails. | **Logic Controller** |
| `extract_with_v2_local` | **Deep Extraction.** Uses GLiNER to find any entity type (Person, Location, etc.) via zero-shot learning. | **GLiNER** (`urchade/gliner_large-v2.1`) |
| `extract_with_v1_local` | **Basic Extraction.** Uses standard syntactic matching to find entities quickly on CPU. | **SpaCy** (`en_core_web_sm`) |

## 4. Summarization (`summarization.py`)

| Function | Motive | Library Used |
| :--- | :--- | :--- |
| **`summarize`** | **The Main Entry Point.** Checks input length and routes to Abstractive (BART) or Extractive (Sumy). | **Logic Controller** |
| `summarize_abstractive_v2` | **Human-like Summary.** Generates completely new sentences to summarize the text (BART). | **Transformers** (`facebook/bart-large-cnn`) |
| `summarize_extractive_v1` | **Sentence Selection.** Picks the 3 most important existing sentences from the text using math (LSA). | **Sumy** |

## 5. Keyword Extraction (`keyword_extraction.py`)

| Function | Motive | Library Used |
| :--- | :--- | :--- |
| **`extract`** | **The Main Entry Point.** Decides between T5 (short text) and Cloud/Fallback models. | **Logic Controller** |
| `_extract_with_t5` | **Generative Keywords.** Asks the T5 model to "generate keywords" for the text. | **Transformers** (`t5-small` / `vlt5`) |
| `_extract_with_keybert_v1` | **Semantic Keywords.** Uses embeddings to find words in the text that represent the whole document. | **KeyBERT** / **SentenceTransformers** |

## 6. Category Classification (`category_classifier.py`)

| Function | Motive | Library Used |
| :--- | :--- | :--- |
| **`classify_category`** | **The Main Entry Point.** Runs Zero-Shot classification and manages the fallback logic. | **Logic Controller** |
| `_classifier_pipeline` (call) | **AI Classification.** Asks BART "Is this text about politics, sports, or business?" without needing training. | **Transformers** (`bart-large-mnli`) |
| *Regex Fallback Logic* | **Keyword Classification.** Counts keyword hits (e.g., "touchdown" = sports) if the AI fails. | **Regex** (`re`) |

## 7. Location Extraction (`location_extraction.py`)

| Function | Motive | Library Used |
| :--- | :--- | :--- |
| **`extract_locations`** | **The Main Entry Point.** Coordinates NER detection + Geocoding enrichment. | **Logic Controller** |
| `ner_service.extract_entities` | **Detection.** Finds location names in the text. | **GLiNER** / **SpaCy** |
| `_cached_geocode` | **Enrichment.** Asks OpenStreetMap "Where is this city?" to get Country/Continent data. | **Geopy** (`Nominatim`) |

## 8. Embeddings & Search (`vector_retriever.py` / `embeddings.py`)

| Function | Motive | Library Used |
| :--- | :--- | :--- |
| **`get_model`** | **Model Loading.** Loads the production-grade E5 model onto the GPU. | **SentenceTransformers** (`multilingual-e5-large`) |
| `get_cached_embedding` | **Vector Generation.** Converts query text into a list of 1024 numbers (the vector) for searching. | **SentenceTransformers** |
| `vector_search` | **The Search Engine.** Sends the generated vector to MongoDB Atlas to find similar articles. | **PyMongo** / **MongoDB Atlas** |
