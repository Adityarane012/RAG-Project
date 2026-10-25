# Explanation faithfulness (scored by independent Claude agents (LLM judges), not humans)

- explanations scored: **28**; factual claims checked: 98; supported by the shown card passages: 80
- claims supported: **81.6%**
- explanations with every claim supported: **50.0%**

## Unsupported claims (notes)

- `q006|abhishekgautamm/whisper-tiny-hinglish-v2`: commercial-use suitability not stated in card
- `q007|Open4bits/whisper-base-f16`: Gujarati support not stated (only generic multilingual ASR)
- `q011|patrickvonplaten/wav2vec2_tiny_random_robust`: accent robustness not stated in metadata
- `q015|dkubeio/DKube-asr-hinglish-v1-0.8B`: suitability for lecture transcription not stated (card warns of out-of-domain errors)
- `q017|DireDreadlord/Vakya-Mini-Extended-100M`: size below 500 MB not stated (only ~100M params, no MB figure)
- `q022|vijaysarathy/indictrans2-indic-en-multilingual-ft`: contradicts card: direction is Indic to English not English to Telugu
- `q023|Helsinki-NLP/opus-mt-ur-en`: trained on OPUS data not explicitly stated
- `q029|Helsinki-NLP/opus-mt-ml-en`: OPUS as large parallel corpus suitable for news not in card
- `q031|pascalrai/hinglish-twitter-roberta-base-sentiment`: usefulness for Hindi and commercial setting not stated
- `q035|kingshukroy/twhin-bert-base-hate-speech-ben-hin`: commercial-use suitability not stated
- `q055|SIRIS-Lab/citation-parser-ENTITY`: generic NER capability applicable to Urdu not in card; lightweight/smaller-than-BERT not stated in passages
- `q058|hiteshwadhwani/pii-model-indic-v1`: small size and open-source nature not stated in passages
- `q065|l3cube-pune/telugu-sentence-bert-nli`: claim that NLI models learn entailment/contradiction is not in passages
- `q072|l3cube-pune/punjabi-sentence-bert-nli`: Sentence Transformers API usage and redistribution not stated
