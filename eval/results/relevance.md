# Relevance @5 (hand-labelled, blind)

Queries fully labelled: **40 of 40**. One labeller; grades 0/1/2 against the purpose of the request (size and license are checked automatically, not graded).

| System | Queries | Models graded | Mean grade | Queries with a grade-2 model % | Models graded 1 or 2 % |
|---|---|---|---|---|---|
| hf_licensed | 40 | 200 | 0.76 | 37.5 | 64.0 |
| keyword | 40 | 197 | 1.112 | 77.5 | 64.5 |
| naive | 40 | 200 | 1.305 | 90.0 | 69.5 |
| ours | 38 | 190 | 1.416 | 84.2 | 80.0 |

## Test-retest agreement (same labeller, repeat pass)

- items graded twice: 266; identical grade on **94.0%**
- Cohen's kappa: nominal **0.907**, quadratic-weighted **0.961**
- 0-versus-2 disagreements: 0

This is self-consistency of one labeller, not inter-annotator agreement.
