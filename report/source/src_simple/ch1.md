# Introduction

A model website is only useful if you can find the right model on it. Hugging Face hosts more than a million ready-made AI models. Suppose a developer wants "a small Marathi named-entity model that I can use in a commercial product". Today they have to turn this into filters for task, language, licence and size, and then open model pages one by one to check. We built HF Model Finder to do this for them, and to make sure the answer can be trusted on size, licence, language and task.

## Background

Retrieval-augmented generation (RAG) means looking up relevant documents first and then giving them to a language model, so that it answers from real text instead of memory [@lewis2020]; a survey describes the many versions of this idea [@gao2023rag]. Searching works in two common ways: by meaning, using "embeddings" that turn text into numbers [@karpukhin2020], and by matching words, as in the classic BM25 method [@robertson2009]. A second model can then re-order the results to put the best first [@nogueira2019]. Embeddings that work across many languages, including Indian ones, also exist [@wang2024me5]. Language models have also been used to pick Hugging Face models for a task [@shen2023]. The problem is the data itself: studies show that model documentation is often incomplete [@jiang2023] and that licences are often missing or wrong on hosting sites [@longpre2024].

## Motivation and scope

A request like "a Marathi NER model under 500 MB, usable commercially, that works well on noisy social-media text" has one soft wish (works well on noisy text) and several hard rules (task, language, size, commercial use). Keyword search cannot understand meaning. The Hugging Face licence filter only matches a licence name and does not know what it allows. Plain RAG suggests models whose pages *sound* right: in our tests it suggested a model that breaks a rule for 50.4% of its suggestions. Data is also often missing: about 27% of the models in our first collection have no clear size.

We cover a snapshot of 15,991 models in eleven tasks: speech recognition, translation, text classification, named-entity recognition, sentence similarity, image classification, object detection, image segmentation, text generation, summarization and question answering. The tool does not run models, give legal advice or rank models by benchmark scores.

## Problem statement

**Build and test a tool that suggests Hugging Face models and checks every suggestion, in code, against each hard rule the user gave (task, language, size, commercial use, modification rights); that says "unknown" when the data is missing; that asks a question when the request is unclear; and that does better on these rules than plain RAG, keyword search and the Hugging Face filters, with a focus on Indian-language models.**

## What we contributed

1. **Code does the checking.** The language model only reads the request and writes explanations. Pass, fail or unknown is decided by ordinary code from the model's data.
2. **"Unknown" is a real answer.** Missing data is shown, not guessed, and a banner appears when nothing could be fully checked.
3. **Licences are turned into rights** (can I use it commercially? can I change it?) and size is calculated by one fixed rule.
4. **Check many, show few.** We check 100 models and show the best 5.
5. **Easy for beginners:** follow-up questions, a plain-English summary of what we understood, a starter code snippet and fine-tuning advice.
6. **A fair test** on 100 questions written before tuning, with its limits stated.
