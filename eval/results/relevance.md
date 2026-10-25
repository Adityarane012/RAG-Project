# Relevance @5 (blind; graded by independent Claude agents (LLM judges), not humans)

Queries fully graded: **40 of 40**. Grades 0/1/2 against the purpose of the request (size and license are checked automatically, not graded).

| System | Queries | Models graded | Mean grade | Queries with a grade-2 model % | Models graded 1 or 2 % |
|---|---|---|---|---|---|
| hf_licensed | 40 | 200 | 0.685 | 22.5 | 61.5 |
| keyword | 40 | 197 | 1.061 | 65.0 | 70.1 |
| naive | 40 | 200 | 0.865 | 67.5 | 51.5 |
| ours | 38 | 190 | 1.284 | 81.6 | 76.8 |

## Agreement between the two grading passes

- items graded twice: 266; identical grade on **92.1%**
- Cohen's kappa: nominal **0.874**, quadratic-weighted **0.945**
- 0-versus-2 disagreements: 0

Both passes were made by: independent Claude agents (LLM judges), not humans. This is agreement between two independent passes by the same kind of grader (test-retest of one labeller, or two LLM passes), not agreement between independent humans.
