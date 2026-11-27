# CodeBench: Real-World Coding Tasks for AI Agents (built with Harbor)

A set of **15 small, real-world coding tasks** with automatic checkers, built on the
[Harbor](https://github.com/harbor-framework/harbor) framework. An AI agent tries each task
inside a container, a hidden test decides pass or fail, and that result is the **reward**
(1 = pass, 0 = fail). The results show where the AI is strong and where it fails.

## The tasks

| Type | Count | What the AI must do |
|---|---|---|
| Logic and edge cases | 3 | Fix functions that break on empty input, negatives, unsorted data |
| Flask APIs | 5 | Fix status codes, validation, pagination, auth and CRUD bugs |
| SQL | 4 | Write queries (aggregation, LEFT JOIN, top-per-group) on a SQLite database |
| Data cleaning | 3 | Write a CSV cleaner (trim, normalize, merge duplicates) |

Difficulty: 4 easy, 7 medium, 4 hard.

Every task folder contains `instruction.md` (the question), `environment/` (the container and
starter code), `tests/` (the hidden checker that writes the reward) and `solution/` (a reference
answer that proves the task is fair).

## How to run

```bash
pip install harbor pytest flask matplotlib
python generate_tasks.py --check    # local check: starter code fails, solutions pass
python generate_tasks.py            # writes the tasks into ./tasks
# run the reference solutions through Harbor (reward should be 1 for every task)
# run an AI agent through Harbor      (see `harbor run --help`)
python analyze.py jobs              # pass rate tables and chart
```

## Results

_Fill this in after your runs: the pass-rate table, `results/pass_rate.png`, and 3-5 lines on
what the agent got wrong and why._

## What I learned

_Write 4-5 honest lines: which tasks were hardest to make fair, which test you had to fix,
what surprised you about the AI's mistakes._