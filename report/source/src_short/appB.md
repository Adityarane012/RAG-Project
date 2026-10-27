# Appendix B: Data Sheet of the Snapshot

The snapshot (SHA-256 `45814b8c…`, 25 October 2026) holds one record per Hub model: identifier, task, downloads, languages and status, size and status, parameters, commercial and modification rights, base model, directions and documentation quality. For each task the top 1,000 models by downloads were fetched, plus all models tagged with ten Indic languages for the language tasks (two transient fetch failures). Size, rights, languages and direction follow the rules of Section 3.4; unknown is preserved. It is intended for verifying constraints, check-a-model and evaluation, and not for ranking quality or legal advice.

::: table b_tasks size=8 cols=3.6,1.4,1.7,1.9,1.9
Composition of the snapshot by task.
| Task | Models | Size unknown | Commercial *yes* | Commercial *unknown* |
|:--|:-:|:-:|:-:|:-:|
| automatic-speech-recognition | 3,469 | 993 | 2,989 | 372 |
| translation | 1,886 | 812 | 1,241 | 290 |
| text-classification | 1,617 | 355 | 1,096 | 388 |
| token-classification | 1,409 | 284 | 1,200 | 156 |
| sentence-similarity | 1,383 | 208 | 1,006 | 284 |
| text-generation | 1,135 | 396 | 668 | 295 |
| question-answering | 1,077 | 263 | 655 | 355 |
| summarization | 1,015 | 130 | 571 | 407 |
| image-classification | 1,000 | 62 | 793 | 153 |
| object-detection | 1,000 | 746 | 479 | 195 |
| image-segmentation | 1,000 | 463 | 544 | 314 |
| **All tasks** | **15,991** | **4,712** | **11,242** | **3,209** |
:::
