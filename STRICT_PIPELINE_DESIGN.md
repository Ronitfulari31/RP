# Strict NLP Pipeline Compliance Report

**Status:** ✅ COMPLIANT (With Cleanup Recommendations)
**Date:** 2026-01-22
**Reviewer:** Antigravity (Senior NLP Systems Engineer)

This report validates the active NLP pipeline against the mandatory approved library list.

---

## 1️⃣ Translation
*   **Primary (Tier 1)**: NLLB-200 (via `transformers`)
    *   *Model*: `facebook/nllb-200-distilled-600M` [GPU]
*   **Fallback (Tier 2)**: Argos Translate (`argostranslate`)
    *   *Note*: Runs offline using installed packages [CPU].
*   **Compliance**: **YES**

## 2️⃣ Named Entity Recognition (NER)
*   **Primary (Tier 1)**: GLiNER (`gliner`)
    *   *Model*: `urchade/gliner_large-v2.1` [GPU]
*   **Fallback (Tier 3)**: SpaCy (`spacy`)
    *   *Model*: `en_core_web_sm` [CPU]
*   **Compliance**: **YES**

## 3️⃣ Sentiment Analysis
*   **Primary (Tier 1)**: RoBERTa (via `transformers`)
    *   *Model*: `cardiffnlp/twitter-roberta-base-sentiment-latest` [GPU]
*   **Fallback (Tier 3)**: BERTweet (via `transformers`)
    *   *Model*: `finiteautomata/bertweet-base-sentiment-analysis` [GPU]
*   **Compliance**: **YES**
*   **Safety Net**: The codebase contains legacy methods for VADER and TextBlob. The main pipeline currently falls back to BERTweet before defaulting to "neutral," ensuring compliant routing.

## 4️⃣ Summarization
*   **Primary (Tier 1)**: BART (via `transformers`)
    *   *Model*: `facebook/bart-large-cnn` [GPU]
*   **Fallback (Tier 3)**: Sumy (`sumy`)
    *   *Algorithm*: LSA (Latent Semantic Analysis) [CPU]
*   **Compliance**: **YES**

## 5️⃣ Keyword Extraction
*   **Primary (Tier 1/2)**: T5 (via `transformers`)
    *   *Model*: `t5-small` (local) or `Voicelab/vlt5-base-keywords` [GPU]
*   **Fallback (Tier 3)**: KeyBERT (`keybert`)
    *   *Backend*: `sentence-transformers` [GPU/CPU]
*   **Compliance**: **YES**

## 6️⃣ Category Classification
*   **Primary**: BART (via `transformers`)
    *   *Model*: `facebook/bart-large-mnli` (Zero-Shot) [GPU]
*   **Fallback**: Keyword Matching (Custom Logic)
    *   *Note*: Uses Python dictionaries and Regex to match domain-specific keywords.
*   **Compliance**: **YES**

## 7️⃣ Preprocessing
*   **Primary**: Standard Python Regex (`re`) and `unicodedata`
    *   *Ops*: Normalization, HTML stripping, emoji removal, whitespace cleanup.
*   **Fallback**: `re` and `html.parser`
*   **Compliance**: **YES**

## 8️⃣ Language Detection
*   **Primary (Tier 1)**: Transformers (`qanastek/51-languages-classifier`) [GPU]
*   **Fallback (Tier 3)**: Langdetect (`langdetect`) [CPU]
*   **Compliance**: **YES**

---

## 📌 Translation Design Philosophy
Translation in this pipeline follows the **Faithful / Literal Translation Mode**. It prioritizes architectural faithfulness over reinterpretation or heuristic reinsertion patches.

*   **Global Greedy Decoding**: The system uses `num_beams=1` (Greedy Search) for ALL translations. This forces the model to translate token-by-token, preserving greetings like "Namaste" and entities like "India" without compression.
*   **Zero-Patch Policy**: We do NOT use invasive reinsertion hacks (Entity Locks). Proper names and vocatives are preserved naturally via literal decoding.
*   **Structure-Stable**: Strictly enforces sentence-level mapping and preserves input order for downstream NLP accuracy.
*   **Integrity Monitoring**: Coverage and length ratios are monitored to detect catastrophic chunk loss, ensuring all content remains intact.

*Translations prioritize semantic correctness and token preservation over stylistic fluency. This ensures entities and emotions are neither removed nor reinterpreted.*

---

## 🚨 Critical Functional Gap: Embeddings
*   **Current State**: **MOCKED** (`app/services/dag/nodes/embeddings.py` returns static vector).
*   **Violation**: Non-functional pipeline stage.
*   **Approved Library**: `sentence-transformers` (Model: `intfloat/multilingual-e5-large`) [GPU].
*   **Action**: Un-mock this stage immediately to achieve production-grade status.

## 🛡️ Validation Summary
The system design **strictly adheres** to the model constraints for all active execution paths. The presence of `deep_translator` and `vader` imports is legacy/utility code and does not affect the deterministic routing of the pipeline. To achieve 100% "Code Cleanliness" compliance, these unused functions should be deleted.

## remove the unused libraries and related codes and keep the code clean and optimized 

## update the requirements.txt file with the new libraries and remove the unused libraries and keep one required.txt file 

## update the pipeline.py file to use the new libraries and remove the unused libraries and keep one pipeline.py file 