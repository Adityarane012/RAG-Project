# Conclusion and Future Work

We built and tested HF Model Finder, which suggests Hugging Face models and checks each suggestion against the user's rules in code. Our tests support four conclusions. (1) Checking in code removed rule-breaking suggestions: none on 75 normal questions, against 50.4% for plain RAG and 25.9% to 32.8% for the Hugging Face filters. (2) Saying "unknown" is better than guessing: 83.3% of suggestions were fully checked, and the rest were clearly marked. (3) Checking many models and showing few helps (72.3% to 83.3% fully checked). (4) Checking did not hurt relevance: the AI judges gave our tool the best mean grade (1.28 out of 2).

**Future work.** (1) Have people grade a sample, to confirm the AI judges. (2) Write test questions for all eleven tasks. (3) Reduce "unknown" without guessing, for example by reading custom licence text and more file types. (4) Keep the data fresh automatically. (5) Run a user study comparing our tool with the Hugging Face search.
