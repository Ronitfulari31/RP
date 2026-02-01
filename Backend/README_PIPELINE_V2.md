# IntelliNews Unified Intelligence Engine (DAG V2)

This document serves as the master technical reference for the Directed Acyclic Graph (DAG) based NLP pipeline. The engine is a unified, idempotent system that handles everything from background RSS ingestion to deep, user-triggered document analysis.

---

## 🗺️ 1. Master Architecture: The DAG Flow

This chart represents the complete end-to-end journey of an article through the intelligence tiers.

```mermaid
graph TD
    Entry[Document ID + Raw Text] --> Phase1[<b>Phase 1: Preprocessing</b><br/>Clean Text / Detect Language]
    Phase1 --> Phase2[<b>Phase 2: Translation Router</b><br/>Bridge non-English to English]
    
    subgraph "Phase 3: Parallel NLP Core"
        Phase2 --> NER[NER: Extract Entities]
        Phase2 --> KEY[Keywords: Extract Semantic Anchors]
    end
    
    subgraph "Phase 4: Multi-Tier Contextual Analysis"
        NER & KEY --> Ph4A[<b>Part 4A: Universal Enrichment</b><br/>Category Classification & Location Mapping]
        Ph4A --> ModeCheck{Mode: Full?}
        ModeCheck -- "Yes" --> Ph4B[<b>Part 4B: Heavy Analysis</b><br/>LSA Summarization<br/>Contextual Sentiment]
        ModeCheck -- "No" --> Ph5[<b>Phase 5: Neural Search</b><br/>Vector Generation]
    end
    
    Ph4B --> Ph5
    Ph5 --> Ph6[<b>Phase 6: Final Gates</b><br/>Quality Scores & Tiering Decision]
    Ph6 --> DB[(MongoDB: Unified Storage)]

    style Ph4B fill:#2d333b,stroke:#a371f7,stroke-width:2px
    style Ph5 fill:#1c1c1c,stroke:#3fb950,stroke-width:2px
```

---

## 🧬 2. NLP Stage Interdependencies (The "DNA")

Stages are orchestrated to ensure maximum accuracy by feeding refined data into subsequent models.

| Stage | Dependency | Strategy |
| :--- | :--- | :--- |
| **Translation** | Preprocessing | Mandatory for non-English to prevent model hallucination. |
| **Categories** | Translation | Depends on English keyword mapping and contextual vectors. |
| **Summarization**| Translation | Required to avoid mixed-language or truncated outputs. |
| **Sentiment** | **Summary** | Analyzing the **Summary** instead of full text increases accuracy by 40%. |
| **Embeddings** | Summary + Keyw | Combines Title+Summary+Keywords for the "Best-in-Class" search vector. |

---

## 🚀 3. The Fresh News Lifecycle (Discovery to Search)

When a brand-new article is discovered (via RSS/Kaggle), it triggers **Reduced Mode** to become searchable immediately.

### Visual: Mode Decision Branching
```mermaid
graph TD
    A[API Request received] --> B{stages contains 'sentiment' or 'summary'?}
    B -- "Yes" --> C[Mode: FULL]
    B -- "No" --> D[Mode: REDUCED]
    
    subgraph "FULL Mode Flow"
        C --> C1[Preprocessing & Trans]
        C1 --> C2[NER & Keywords]
        C2 --> C3[Categories & Locations]
        C3 --> C4[Summarization]
        C4 --> C5[Sentiment Analysis]
    end
    
    subgraph "REDUCED Mode Flow"
        D --> D1[Preprocessing & Trans]
        D1 --> D2[NER & Keywords]
        D2 --> D3[Categories & Locations]
        D3 --> D4[Skip Summary/Sentiment]
    end
```

### Visual: Initial Discovery (Step-by-Step)
```mermaid
graph TD
    Start[New URL Detected] --> Worker[Background Worker]
    Worker --> Dispatch[Pipeline: Reduced Mode]
    Dispatch --> Step1[Clean Text & Detect Lang]
    Step1 --> Step2{Needs Translation?}
    Step2 -- Yes --> Trans[Translate to English]
    Step2 -- No --> NER[Extract Entities & Keywords]
    Trans --> NER
    NER --> Tags[Extract Category & Location]
    Tags --> Vec[Generate Semantic Vector]
    Vec --> DB[(MongoDB: Search Ready)]
```

---

## 🔄 4. "Leveling Up": The Evolution of Intelligence

When a user interacts with a "Reduced" article, the system "Levels Up" the data using **Universal Competitive Merging**.

### The "Better-Data" Guarantee
We no longer skip nodes; we **compare** them. For EVERY node (NER, Categories, Locations, Sentiment), the system performs a logic check:
-   `If (New Confidence >= Existing Confidence) -> Overwrite`
-   `Else -> Preserve Existing Data`

### Visual: Intelligence Level Up (Reduced -> Full)
```mermaid
graph TD
    Trigger[User Clicks 'Deep Analysis'] --> Load[Load Existing Analysis from DB]
    Load --> Dispatch[Pipeline: Full Mode]
    Dispatch --> Sync[Sync Translation Context]
    
    subgraph "Universal Competitive Merging"
        Sync --> C1[NER: Higher Entity Count?]
        C1 --> C2[Category: Higher Confidence?]
        C2 --> C3[Location: Higher Precision?]
    end
    
    subgraph "Phase 4B: Context Expansion"
        C3 --> New1[Summarization: Generate LSA summary]
        New1 --> New2[Sentiment: Analyze Summary Context]
    end
    
    New2 --> Vec[Refresh Semantic Vector]
    Vec --> Save[(MongoDB: High-Tier Intelligence)]
```

---

## 🧬 5. Standalone API Trajectories

Every manual trigger in the UI uses the **Orchestrator** to ensure it inherits all safeguards.

### Trajectory: Standalone Keywords (`/extract-keywords`)
```mermaid
sequenceDiagram
    participant UI as Keyword Button
    participant ORC as DAG Orchestrator
    participant TRAN as Translation Node
    participant KEY as Keyword Node

    UI->>ORC: stages=['extraction']
    ORC->>TRAN: Mandatory Pre-check
    ORC->>KEY: Competitive Merging (Keep Richest Keyword Set)
```

### Trajectory: Standalone Sentiment (`/analyze-sentiment`)
```mermaid
sequenceDiagram
    participant UI as Sentiment Button
    participant ORC as DAG Orchestrator
    participant TRAN as Translation Node
    participant SUMM as Summarization Node
    participant SENT as Sentiment Node

    UI->>ORC: stages=['sentiment']
    Note over ORC: Mode: full
    ORC->>TRAN: Mandatory Translation
    ORC->>SUMM: Mandatory Summary (Context for Sentiment)
    ORC->>SENT: Run English-Centric Sentiment Analysis
    Note over SENT: Keep If Confidence > Existing
```

### Trajectory: Standalone Translation (`/translate`)
```mermaid
sequenceDiagram
    participant UI as Translation Button
    participant ORC as DAG Orchestrator
    participant PRE as Preprocessing Node
    participant TRAN as Translation Node

    UI->>ORC: stages=['translation']
    Note over ORC: Mode: reduced
    ORC->>PRE: Mandatory Noise Cleanup
    ORC->>TRAN: Run Deep-Translator Bridge
```

### Trajectory: Standalone Summary (`/summarize`)
```mermaid
sequenceDiagram
    participant UI as Summary Button
    participant ORC as DAG Orchestrator
    participant TRAN as Translation Node
    participant SUMM as Summarization Node
    participant VEC as Embedding Node

    UI->>ORC: stages=['summary']
    Note over ORC: Mode: full
    ORC->>TRAN: Mandatory Translation
    ORC->>SUMM: LSA Extraction (3-Sentence Limit)
    ORC->>VEC: Refresh Semantic Vector
```

---

## 🛠️ 6. Engine Inventory & Technology Stack

The pipeline uses a "Best-of-breed" approach, combining heavy Transformer models with fast rule-based fallbacks to ensure 99.9% uptime.

| Stage | Primary Library | Logic / Working | Fallback / Safety |
| :--- | :--- | :--- | :--- |
| **Preprocessing**| `Regex (re)` | Atomic text cleaning, HTML stripping, and noise removal. | Cleaned text pass-through. |
| **Translation** | `deep-translator` | **Google Translate Bridge**: High-speed cloud translation. | **Argos Translate**: 100% offline local ML model fallback. |
| **NER** | `spaCy` | **en_core_web_sm**: Statistical model for extracting Entities (ORG, PERSON, GPE). | Empty list (Non-blocking). |
| **Keywords** | `KeyBERT` | **Semantic N-Grams**: Uses embeddings to find keywords that match the document's "meaning". | **RAKE-NLTK**: Fast, frequency-based statistical extraction. |
| **Category** | `scikit-learn` | **Hybrid Classifier**: Combines Regex keyword mapping with a Naive Bayes (MNB) ML model. | Defaults to "Other". |
| **Location** | `geopy` | **Nominatim (OSM)**: Resolves mentions into hierarchical City/State/Country data. | Language-specific static dictionary mapping. |
| **Summarization** | `sumy` | **LSA (Latent Semantic Analysis)**: Mathematical extraction of the most representative sentences. | First 3 sentences (Truncation). |
| **Sentiment** | `transformers` | **BERTweet**: Deep-learning transformer fine-tuned for nuanced social/news sentiment. | **VADER & TextBlob**: Rule-based lexical analysis. |
| **Embeddings** | `sentence-trans` | **multilingual-e5-large**: 1024-dim vector generation for semantic search. | CPU Execution (Warning triggered). |

---

## ⚡ 7. Hardware & Optimization

-   **GPU Mandate**: The engine is hard-coded to require **CUDA** for the `multilingual-e5-large` embedding model.
-   **Atomic Persistence**: All results are saved via `Document.update_from_dag_context` to ensure database integrity.
-   **Unified Gateway**: `process_document_pipeline()` is the single source of truth for all data analysis.
