# HF Model Finder — Comprehensive Query Catalog (`queries_search.md`)

This catalog lists queries for testing, demonstrating, and evaluating **HF Model Finder** (Constraint-Verified RAG for Hugging Face Models). 

The underlying corpus contains **15,991 Hugging Face models** and **48,179 indexed chunks** across 11 tasks (the 5 original tasks below, plus image classification, object detection, image segmentation, text generation, summarization and question answering, added 2026-10-25; the catalog below was written for the original five):
1. `automatic-speech-recognition` (Speech-to-Text)
2. `translation` (Machine Translation)
3. `token-classification` (Named Entity Recognition / NER)
4. `text-classification` (Sentiment Analysis / Topic Classification)
5. `sentence-similarity` (Sentence Embeddings / Semantic Search)

---

## Table of Contents
1. [Standard English & Everyday Industry Models](#1-standard-english--everyday-industry-models)
2. [Top Showcase & Demo Queries (Indic & Multi-Constraint)](#2-top-showcase--demo-queries-indic--multi-constraint)
3. [Task-Specific Queries by Language](#3-task-specific-queries-by-language)
   - [Speech Recognition (ASR)](#speech-recognition-asr)
   - [Machine Translation](#machine-translation)
   - [Named Entity Recognition (NER)](#named-entity-recognition-ner)
   - [Text Classification & Sentiment](#text-classification--sentiment)
   - [Sentence Similarity & Embeddings](#sentence-similarity--embeddings)
4. [Constraint & License Test Queries](#4-constraint--license-test-queries)
   - [Strict Commercial Use](#strict-commercial-use)
   - [Permissive Open-Source (MIT / Apache 2.0)](#permissive-open-source-mit--apache-20)
   - [Modifiable / Fine-Tunable Only](#modifiable--fine-tunable-only)
   - [Edge & Low-Memory (< 500 MB / Laptop-Friendly)](#edge--low-memory--500-mb--laptop-friendly)
5. [Native Script Queries (Devanagari & Indic)](#5-native-script-queries-devanagari--indic)
6. [Interactive Edge Cases](#6-interactive-edge-cases)
   - [Clarification Triggers (Vague Queries)](#clarification-triggers-vague-queries)
   - [Relaxation Triggers (Impossible / Over-Constrained)](#relaxation-triggers-impossible--over-constrained)
   - [Naive RAG Contrast Queries (Baseline Flaws)](#naive-rag-contrast-queries-baseline-flaws)
7. [Model ID Verification ("Check a Model" Tab)](#7-model-id-verification-check-a-model-tab)
8. [How to Run & Test These Queries](#8-how-to-run--test-these-queries)

---

## 1. Standard English & Everyday Industry Models

While the research paper highlights Indic and low-resource constraints (where metadata is notoriously messy), **the index includes the top 1,000 global models per task by downloads** on Hugging Face (Whisper, RoBERTa, BERT, MiniLM, ModernBERT, Opus-MT, etc.). 

Use these "normal" everyday English queries to test standard production workloads:

| Query | Target Task | Expected Verified Models | Key Check |
|---|---|---|---|
| `Fast English speech recognition under 500 MB` | `automatic-speech-recognition` | `Open4bits/whisper-base-f16`, `Open4bits/whisper-tiny-f16`, `aufklarer/Nemotron-3.5-ASR...` | Size constraint (<500 MB) + English ASR verification |
| `English sentiment analysis for product reviews that I can use commercially` | `text-classification` | `tabularisai/robust-sentiment-analysis`, `cirimus/modernbert-base-go-emotions`, `nlptown/bert...` | Apache-2.0 / MIT commercial pass; rejects non-commercial models |
| `Fast English sentence embeddings under 200 MB for semantic search` | `sentence-similarity` | `yrrhall/gemma-student-gemma_emb_mrl_distilled_128d`, `axiotic/ogma-small` | Sub-200 MB size limit + dense embedding retrieval |
| `English named entity recognition model with permissive license` | `token-classification` | `dslim/bert-base-NER`, `dbmdz/bert-large-cased-finetuned-conll03-english` | CoNLL-03 token classification + Apache/MIT license |
| `English to French translation under 500 MB` | `translation` | `Helsinki-NLP/opus-mt-en-fr` | Directional `en -> fr` mapping + lightweight weight check |
| `Twitter emotion detection model for commercial use` | `text-classification` | `cardiffnlp/twitter-roberta-base-emotion-latest` | Social media text classification + commercial rights |
| `Customer support intent classification model, commercial use` | `text-classification` | `modernbert-base`, `distilbert` sentiment & intent | Commercial pass + text classification |

---

## 2. Top Showcase & Demo Queries (Indic & Multi-Constraint)

These queries demonstrate key features during presentations and live evaluation:

| # | Query | Key Demonstration | Expected Outcome |
|---|---|---|---|
| **D1** | `Small sentiment model for Hindi I can use in a commercial app` | Commercial filter + task + language + size verification | Returns verified Apache/MIT models (e.g. `l3cube-pune/hindi-sentiment-bert`); flags non-commercial baselines. |
| **D2** | `Commercial Hindi to Marathi translation` | Translation direction + cross-lingual verification | Verifies source and target language pairs; eliminates unidirectional models going the wrong way. |
| **D3** | `I want a Hindi model` | Ambiguity detection & Clarification dialog | System asks: *"Which task do you need a model for?"* with interactive task buttons. |
| **D4** | `Marathi NER model I can use commercially` | Token classification + license rights parsing | Returns verified Marathi NER models; shows "Try it" inference snippet and "Build on it" guide. |
| **D5** | `Hindi to Marathi translation under 1 MB` | Over-constrained relaxation loop | System detects 0 models under 1 MB; proposes relaxing size limit to 300 MB or 500 MB. |
| **D6** | `Urdu to English translation I can use in a product` | Directional license verification | Distinguishes between verified direction and generic multilingual models. |
| **D7** | `Tamil NER model I can fine-tune` | Modifiability rights check | Filters for licenses that explicitly grant derivative and fine-tuning rights. |

---

## 2. Task-Specific Queries by Language

### Speech Recognition (ASR)
- `Speech recognition for Tamil under 1 GB`
- `Hindi speech recognition model small enough to run on a laptop`
- `I need a Marathi ASR model I can use commercially`
- `Bengali automatic speech recognition, Apache or MIT licensed`
- `Telugu transcription model that I can fine-tune and sell`
- `Speech to text for Gujarati, commercial use allowed, under 1 GB`
- `Kannada speech recognition trained on noisy real-world recordings`
- `Malayalam ASR model, medium size, usable in a paid product`
- `Punjabi voice transcription, tiny model please`
- `Speech recognition for lectures in Hindi, I want to fine-tune it later`

### Machine Translation
- `Hindi to English translation model, commercial use`
- `English to Hindi machine translation under 500 MB`
- `Commercial Hindi to Marathi translation`
- `Translate Tamil to English, small model`
- `Bengali to English translation model with permissive license`
- `Gujarati to English translator for conversational text`
- `Telugu to English machine translation, commercial friendly`
- `Kannada to English translation model under 1 GB`
- `Malayalam to English translator that I can modify`
- `Urdu to English translation for customer support chat`

### Named Entity Recognition (NER)
- `Marathi NER model under 500 MB for noisy social-media text`
- `Hindi named entity recognition model with Apache 2.0 license`
- `Tamil token classification model for news articles`
- `Bengali NER model that can recognize person and organization names`
- `Telugu named entity recognition I can deploy commercially`
- `Odia named entity recognition model for news text, free to modify`
- `Gujarati NER model small enough for mobile deployment`
- `Kannada token classification model for legal documents`
- `Multilingual NER model covering Hindi, Marathi, and Bengali`

### Text Classification & Sentiment
- `Small sentiment model for Hindi I can use in a commercial app`
- `Marathi sentiment analysis model with an open source license`
- `Bengali text classification for customer reviews`
- `Tamil sentiment classifier under 300 MB`
- `Telugu intent classification for chatbot development`
- `Kannada sentiment classifier with an MIT license`
- `Gujarati topic classification model, commercial use allowed`
- `Malayalam sentiment analysis model I can fine-tune`

### Sentence Similarity & Embeddings
- `Sentence embeddings for Bengali that I can modify and sell`
- `Hindi sentence similarity model under 500 MB`
- `Marathi sentence transformers for semantic search`
- `Tamil embedding model for duplicate question detection`
- `Telugu sentence embeddings with commercial license`
- `Nepali sentence similarity model I can modify`
- `Multilingual Indic sentence similarity covering 10+ languages`

---

## 3. Constraint & License Test Queries

### Strict Commercial Use
- `Commercial Hindi to Marathi translation`
- `Marathi NER model I can use commercially`
- `Speech recognition for Tamil commercial use allowed`
- `Sinhala speech recognition model, commercial use`
- `Gujarati text classification model with commercial rights`

### Permissive Open-Source (MIT / Apache 2.0)
- `Bengali automatic speech recognition, Apache or MIT licensed`
- `Kannada sentiment classifier with an MIT license`
- `Hindi NER model with Apache-2.0 license`
- `Small Gujarati text classification model with a permissive license`
- `Tamil speech recognition with MIT license under 500 MB`

### Modifiable / Fine-Tunable Only
- `Tamil NER model I can fine-tune`
- `Telugu transcription model that I can fine-tune and sell`
- `Sentence embeddings for Bengali that I can modify and sell`
- `Malayalam to English translator that I can modify`
- `Nepali sentence similarity model I can modify`

### Edge & Low-Memory (< 500 MB / Laptop-Friendly)
- `English to Hindi machine translation under 500 MB`
- `Hindi to English translation model under 300 MB`
- `Tamil speech-to-text under 500 MB that handles phone call audio`
- `Marathi NER model under 500 MB for noisy social-media text`
- `Hindi speech recognition model small enough to run on a laptop`

---

## 4. Native Script Queries (Devanagari & Indic)

The system normalizes and handles native script inputs:

- `हिंदी के लिए छोटा स्पीच रिकग्निशन मॉडल जो व्यावसायिक उपयोग के लिए ठीक हो` *(Hindi: Small speech recognition model suitable for commercial use)*
- `मराठी ते इंग्रजी भाषांतर मॉडेल, व्यावसायिक वापरासाठी` *(Marathi: Marathi to English translation model for commercial use)*
- `मराठी नाममुद्रा ओळख (NER) मॉडेल` *(Marathi: Named entity recognition model)*
- `தமிழ் பேச்சு पहचान மாதிரி` *(Tamil: Speech recognition model)*
- `বাংলা অনুবাাদক মডেল` *(Bengali: Translation model)*

---

## 5. Interactive Edge Cases

### Clarification Triggers (Vague Queries)
These test whether the system avoids hallucinating when intent is underspecified:
- `I want a Hindi model` *(Triggers task clarification)*
- `A model for Marathi` *(Triggers task clarification)*
- `Translate something` *(Triggers language pair clarification)*
- `Speech model` *(Triggers language clarification)*
- `Fast model for Indian languages` *(Triggers task & language clarification)*

### Relaxation Triggers (Impossible / Over-Constrained)
These test whether the system detects zero matching candidates and suggests reasonable constraint relaxations:
- `Hindi to Marathi translation under 1 MB` *(No translation models are < 1 MB; proposes relaxing to ~300 MB)*
- `Tamil speech recognition under 5 MB with MIT license` *(Proposes relaxing size to 500 MB)*
- `Bengali translation model under 100 KB` *(Proposes relaxing size)*

### Naive RAG Contrast Queries (Baseline Flaws)
*Check the "Compare with naive RAG" checkbox in the UI to see naive failures:*
- `Small sentiment model for Hindi I can use in a commercial app`
  - **Naive RAG**: Returns non-commercial or CC-BY-NC models because it only checks text similarity.
  - **HF Model Finder**: Verifies license metadata and filters out non-commercial candidates.
- `Commercial Hindi to Marathi translation`
  - **Naive RAG**: Recommends Marathi-to-Hindi or general multilingual models that do not support the exact direction.
  - **HF Model Finder**: Formally verifies source (`hi`) and target (`mr`) coverage.
- `Marathi NER model under 500 MB`
  - **Naive RAG**: Recommends 1.5 GB+ BERT models that fail the memory requirement.
  - **HF Model Finder**: Accurately computes model file sizes from repo manifests and rejects oversized models.

---

## 6. Model ID Verification ("Check a Model" Tab)

Test the "Check a model" feature by pasting these model IDs directly:

| Model ID | Primary Task | Key Facts |
|---|---|---|
| `openai/whisper-tiny` | `automatic-speech-recognition` | ~150 MB, Apache 2.0 (Commercial + Modifiable pass) |
| `openai/whisper-small` | `automatic-speech-recognition` | ~960 MB, Apache 2.0 |
| `vasista22/whisper-tamil-small` | `automatic-speech-recognition` | ~960 MB, Tamil fine-tune |
| `Helsinki-NLP/opus-mt-en-hi` | `translation` | ~300 MB, Apache 2.0, English to Hindi |
| `l3cube-pune/marathi-ner` | `token-classification` | ~700 MB, Marathi NER |
| `l3cube-pune/hindi-sentiment-bert` | `text-classification` | ~440 MB, Hindi Sentiment |
| `ai4bharat/indictrans2-indic-indic-1B` | `translation` | Large multi-indic translation |

---

## 7. How to Run & Test These Queries

### 1. In the Web UI
Open the browser at `http://localhost:8501`:
1. Click any of the 5 quick-start buttons on the **Search** tab.
2. Or paste any query from this catalog into the text input.
3. Toggle **"Compare with naive RAG"** to view side-by-side verification tables.

### 2. From the Python Pipeline (CLI)
```bash
python -c "from src.pipeline import build_pipeline; g = build_pipeline('ours'); res = g.invoke({'query': 'Speech recognition for Tamil under 1 GB'}); print(res['outcome'], [r['model_id'] for r in res.get('results', [])])"
```

### 3. In Replay Mode (Offline / 0 Network Calls)
```bash
$env:REPLAY="1"
streamlit run app.py
```
This serves the pre-recorded runs from `demo/cache/` instantly with zero API dependencies.
