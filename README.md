# autospec

**Natural-language domain specs in, working service code out.**

An autonomous keep-or-revert loop — inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — that reads business rules written in plain language and iteratively builds, tests, and verifies a service until the spec is satisfied.

## Demo Results

We wrote 5 domain documents (67 lines of Korean). The orchestrator ran **7 cycles in 26 minutes** and built a complete REST API from a 119-line skeleton:

| Cycle | What the AI Did | Tests | Lines | Time |
|-------|----------------|-------|-------|------|
| 1 | CRUD + validation + status transitions | 1 → 12 | +384 | 4m44s |
| 2 | Error response consistency + edge cases | 12 → 18 | +121 | 5m19s |
| 3 | 500 handler, null status check, test gaps | 18 → 22 | +97 | 4m29s |
| 4 | Lifecycle test, edge case coverage | 22 → 28 | +123 | 5m44s |
| 5 | Transactional safety, input validation tests | 28 → 34 | +101 | 5m58s |
| 6-7 | *(no changes — converged)* | 34 | — | — |

**119-line skeleton → 950 lines of working Java. 34 tests. 5 accepts, 0 rejects. $0 cost.**

## How It Works

```
┌─────────────────────────┐
│  .autospec/domain/*.md  │  Human writes business rules (natural language)
│  .autospec/common/*.md  │  Human writes tech conventions (once)
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│    orchestrator.py      │  Loop controller
│                         │
│  1. Read previous runs  │
│  2. Build prompt        │
│  3. Call claude -p      │──► Claude Code CLI reads specs, writes code, commits
│  4. Evaluate result     │
│  5. Accept or reject    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│     evaluator.py        │  Judge (no AI)
│                         │
│  ./gradlew build        │
│  Parse JUnit XML        │
│                         │
│  Accept: build pass     │
│    + tests pass         │
│    + test count ≥ prev  │
│                         │
│  Reject: git reset      │
└─────────────────────────┘
```

The evaluator is **outside the AI**. The AI writes code; a deterministic script judges it.

## Quick Start

```bash
git clone https://github.com/jeongph/autospec.git
cd autospec

# Requires: Java 17, Python 3, Claude Code CLI
python orchestrator.py examples/spring-boot-todo
```

## Domain Documents

Domain docs are pure natural language — no code, no types, no API paths:

> 할일을 만들면 "대기" 상태가 된다.
> 작업을 시작하면 "진행중"으로 바뀌고, 끝나면 "완료"가 된다.
> 완료된 할일은 다시 되돌릴 수 없다.

The AI reads this, maps "대기" to `PENDING`, figures out which endpoint handles status changes, and writes the validation logic.

Technical conventions (response format, naming, DB) live in `.autospec/common/` — separated from business rules.

## Project Structure

```
autospec/
├── orchestrator.py          ← Loop controller
├── evaluator.py             ← Build/test judge (no AI)
├── history.py               ← Cycle records + context passing
└── examples/
    └── spring-boot-todo/    ← Example: Todo API
        ├── .autospec/
        │   ├── program.md   ← Agent instructions
        │   ├── common/      ← Tech conventions
        │   ├── domain/      ← Business rules (Korean)
        │   └── eval.md      ← Pass/fail criteria
        └── src/             ← Skeleton (AI fills this)
```

## Safety

- **Reject on build failure** → `git reset --hard HEAD~1`
- **Reject on test failure** → rollback
- **Reject on test regression** → test count cannot decrease
- **Max 3 consecutive failures** → stop
- **Convergence detection** → stop after 2 unchanged cycles
- **10-minute timeout** per cycle

## Autoresearch Correspondence

| autoresearch | autospec |
|---|---|
| `program.md` | `.autospec/program.md` |
| `prepare.py` (immutable) | `evaluator.py` (no AI) |
| `train.py` (AI modifies) | `src/` (AI writes) |
| `val_bpb` | test count + build pass |

## License

[MIT](LICENSE)
