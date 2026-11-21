# Agentic AI Training Lab 2: Retrieval-Augmented Generation

Rich answers you can trust. Course 3, Agentic Systems and Retrieval.

You have built retrieval from primitives. This lab puts it under the conditions a real system meets:
manuals full of figures and tables, sources that disagree, merchants who must never see each other's
terms, and questions the documents cannot answer. Every part uses one fictional company, Aralia
Systems, which sells point-of-sale systems to shops and restaurants in Sri Lanka.

| Part | Where | What you build | Guide |
| --- | --- | --- | --- |
| 1 | In session | Answers that return the real figure or table, with its page | [docs/part1.md](docs/part1.md) |
| 2 | Take-home | Searchable tables and exact identifiers | [docs/part2.md](docs/part2.md) |
| 3 | Take-home | Answers that need several sources, or every ticket | [docs/part3-4.md](docs/part3-4.md) |
| 4 | Take-home | Answers you can trust: current sources, merchant privacy, abstention, injected instructions | [docs/part3-4.md](docs/part3-4.md) |

Every part has dev questions with answers, so you can score yourself as often as you like, and test
questions that facilitators score. Each scorecard ends with a ship gate.

## API key

**You need an API key to do this lab.** Every figure caption and every support answer is a call to a
language model. Use one of:

- **Anthropic:** an `ANTHROPIC_API_KEY` from console.anthropic.com (paid, low cost for this lab).
- **OpenRouter:** an `OPENROUTER_API_KEY` from openrouter.ai. Free models work, with daily limits
  (see Model budget below).

Your facilitator will tell you which to use. The embedding model, all-MiniLM-L6-v2 (the one from
the primitives lab), runs on your laptop and needs no key.

## Setup

You need Python 3.10 or newer and Git.

```
git clone https://github.com/Dinal-Senadheera/agentic-ai-training-lab-2.git
cd agentic-ai-training-lab-2
python -m venv .venv
.venv\Scripts\activate            (Windows Command Prompt)
.venv\Scripts\Activate.ps1        (Windows PowerShell)
source .venv/bin/activate          (macOS, Linux)
pip install -r requirements.txt
copy .env.example .env            (Windows)   or   cp .env.example .env
```

Open `.env` and set `PARTICIPANT` to your ID (letters and digits only), `LLM_PROVIDER` (`anthropic`
or `openrouter`) and the matching key. Then run:

```
lab check
```

It shows your key's limits and the model in use, and makes one text call and one image call. If it
says there is no API key, or the call fails, fix that before the session: nothing else in the lab
works without it. The first run of anything that embeds downloads the embedding model once.

## How you work

You write code in two files and run everything else from the terminal.

| File | What you change |
| --- | --- |
| `mylab/manuals.py` | `MyManuals`: your pipeline for Parts 1 and 2 |
| `mylab/support.py` | `MySupport`: your pipeline for Parts 3 and 4 |

Each class extends a baseline in `labkit/`. Read the baseline first, override one method at a time,
and score after every change so each gain is attributable.

| Command | What it does |
| --- | --- |
| `lab show fsm-fig3 fsm-tab3b` | Print units: provenance, text, table rows, or the figure's image path |
| `lab manuals --pipeline baseline` | Run and score the baseline on the dev questions, and save the run |
| `lab manuals` | Run and score your pipeline, compared with the saved baseline run |
| `lab explain manuals A01` | What your pipeline retrieves and answers for one question, or any text |
| `lab support --ids D03 D16` | Run and score your support assistant on some dev questions |
| `lab support --retrieval-only` | Retrieval metrics with no model calls |
| `lab compare` | The whole corpus in one prompt against RAG, on the same five questions |
| `lab explain support D20` | What the support assistant retrieves, with each chunk's source details |
| `lab rescore runs/mine_support_dev.jsonl` | Score a saved run again, with no model calls |
| `lab submit manuals` / `lab submit support` | Run the test questions once and write your submission |

Add `--pipeline baseline` (or `module:Class`) to any run or explain command to use another
pipeline. `lab <command> --help` lists every option. `python -m labkit` works in place of `lab`.

## Model budget

Part 1 spends model calls only on figure captions, which are cached in `.cache/` after the first
run. A full support dev run makes 24 calls and the test run 26, so use `--ids` and
`--retrieval-only` while developing. On OpenRouter's free models you get 50 requests a day
(1,000 once $10 of credits have ever been bought) and 20 a minute; the kit paces calls to stay
under 20 a minute. `lab check` shows how many free requests you have left today.

## Repository layout

| Path | What it is |
| --- | --- |
| `mylab/` | Your pipelines |
| `labkit/` | Shared code: settings, model calls, embeddings, the baselines, explain tools, scorers, the `lab` command, and an optional Chroma vector store (`vectorstore.py`) |
| `data/manuals/` | Parts 1 and 2: two hardware manuals parsed into units, figures, a loose photo, questions |
| `data/support/` | Parts 3 and 4: the support knowledge base and its questions |
| `docs/` | The lab guide for each part, and the template for your Part 4 decision record |
| `runs/` | Saved dev runs, used for comparisons and rescoring. A run on some questions updates only those |
| `submissions/` | Your test submissions |

## Fair play

Your pipelines see only each question's ID, text and merchant. Do not read gold fields, route on
question IDs, hard-code answers, or edit `labkit/score.py` and `data/`. Run each test split once.
