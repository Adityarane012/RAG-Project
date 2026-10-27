# Screenshots and Results

## What the tool looks like

@fig:ui_compare shows the request "Small sentiment model for Hindi I can use in a commercial app" with the comparison switched on. The line "We understood" shows that "small" was read as 500 MB. On the left is our system: every row passes. On the right is plain RAG on the same data: some of its suggestions have a red cross in the size row. For vague requests such as "I want a Hindi model" the tool asks what the model should do instead of guessing. @fig:ui_banner (a) shows an honest "unknown": for "Hindi to Marathi translation under 1 MB" nothing can be fully checked, so a banner says so. Under each model, "Try it" gives a starter code snippet and "Build on it" shows whether the model can be changed, its parent model, and how much GPU memory fine-tuning needs (b).

::: fig ui_compare w=11
ui_compare_short.png
Our results (left) against plain RAG (right) for a small Hindi sentiment model that can be used commercially.
:::

::: fig ui_banner w=8.8
ui_banner_short.png | (a) Banner when nothing is fully checked
ui_buildon_short.png | (b) Try it and Build on it panels
Unknowns are shown, never guessed.
:::

## Results against the other systems

@tab:main shows the main result on the 75 normal questions. Every system's top five models were judged by the same rules.

::: table main size=9 cols=3.6,1.4,1.2,1.5,1.5,1.7
Main results on 75 normal questions (top five per question).
| System | Answered % | Models | Rule broken % | Unknown % | Fully checked % |
|:--|:-:|:-:|:-:|:-:|:-:|
| **Ours** | 97.3 | 365 | **0.0** | 16.7 | **83.3** |
| Plain RAG | 100.0 | 375 | 50.4 | 20.5 | 29.1 |
| Keyword (BM25) + filters | 100.0 | 368 | 0.0 | 62.0 | 38.0 |
| Hugging Face filters, basic | 100.0 | 375 | 32.8 | 13.6 | 53.6 |
| Hugging Face filters, licence | 100.0 | 375 | 25.9 | 14.7 | 59.5 |
:::

::: fig chart_main w=12
chart_main.png
How each system's suggestions were judged: fully checked, unknown, or breaking a rule.
:::

Our tool suggested no model that breaks a rule, and 83.3% of its suggestions were fully checked, against 29.1% for plain RAG. It answered 73 of 75 questions; on the other two it asked a follow-up question. Plain RAG got the size wrong in 50.4% of its suggestions. The Hugging Face filters cannot filter by size at all and got it wrong in 80.0% (basic) and 71.9% (licence) of suggestions. Keyword search never breaks a rule, because it uses our filters, but 62% of its suggestions are unknown: matching words says nothing about size or licence.

On the 15 vague questions our tool asked a follow-up question every time; the others just answered. Ten questions were meant to be impossible, but a model with unknown size or language never fails, so none could be proved impossible. On the 12 questions where no model in the data fully passes, our tool showed a banner every time and never claimed a model was fully checked; plain RAG and the Hugging Face filters suggested rule-breaking models for 63% to 75% of their suggestions.

## Other checks

AI judges graded how well suggestions fit the request (@tab:relevance). Our tool has the best mean grade, so checking the rules did not hurt relevance. A second pass by other judges agreed on 92.1% of grades (Cohen's kappa [@cohen1960] 0.874, which is "almost perfect" agreement). This shows the judging is consistent, not that it matches people.

::: table relevance size=9 cols=3.6,1.4,1.8,1.6,2.4
Relevance (graded 0 to 2 by AI judges, blind).
| System | Questions | Models graded | Mean grade | Questions with a grade-2 model |
|:--|:-:|:-:|:-:|:-:|
| **Ours** | 38 | 190 | **1.28** | **81.6%** |
| Keyword + filters | 40 | 197 | 1.06 | 65.0% |
| Plain RAG | 40 | 200 | 0.87 | 67.5% |
| Hugging Face filters, licence | 40 | 200 | 0.69 | 22.5% |
:::

AI judges also checked 98 claims in 28 explanations: 80 (81.6%) were backed by the model page, and half of the explanations were fully backed. So explanations are a convenience and not proof; the pass or fail tables do not depend on them. The starter code snippet ran on 20 of 32 small models (the rest need other tools). A normal search takes about 1.3 seconds, and 7 to 17 seconds with the explanation.

## Limits

About 27% to 30% of models have no known size, and about 20% have no usable licence, so no method can check those; the 16.7% "unknown" is close to the best possible on this data. Grading was done by AI judges, not people. The questions were written by the same team that built the tool. The 100 questions cover the original five tasks only; the six newer tasks were spot-checked. Rights come from the *declared* licence and are not legal advice. The data is a snapshot of Hugging Face from 25 October 2026.
