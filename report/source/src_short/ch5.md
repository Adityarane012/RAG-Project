# Source Code

The repository (about 3,600 lines in `src/` and `app.py`, 900 in `eval/`, 3,300 in `tests/`) is at <https://github.com/Adityarane012/RAG-Project>. Everything that decides a verdict is a plain module with no network access; the listings below are the core of `src/verify.py`, copied from the file and line ranges in their captions.

::: code verify cap="src/verify.py (lines 73 to 90): one result per requested constraint." src=src/verify.py lines=73-90
:::

::: code overall cap="src/verify.py (lines 106 to 123): combining results and ranking." src=src/verify.py lines=106-123
:::

::: code filter cap="src/retrieve.py (lines 13 to 43): the metadata filter keeps models whose field is unknown." src=src/retrieve.py lines=13-43
:::
