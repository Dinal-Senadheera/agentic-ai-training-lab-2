# Parts 3 and 4 (take-home): the Aralia support copilot

Aralia's L1 support team answers merchants' questions from a knowledge base of manuals for two
product versions (Classic 3.x and Cloud 4.x), policies, release notes, two merchants' contract
addenda, past tickets, a plans PDF and images. A pilot copilot lost the agents' trust: it quoted
Classic limits to Cloud merchants, gave outdated refund rules, and told a restaurant about another
merchant's contract.

The baseline already does what you built in the primitives lab and more: it fuses BM25 with dense
search, uses a grounded prompt with an abstain option, and receives the images and the plans table
as enriched text. It still fails, because it does not reason about the sources it finds. Read
`CopilotBaseline` in `labkit/copilot.py`, then save a baseline run:

```
lab copilot --pipeline baseline
```

Each full dev run makes 24 model calls, and the test run 26. While developing, run a few questions
with `--ids`, and check retrieval with `--retrieval-only`, which makes no model calls. On
OpenRouter's free models the allowance is 50 requests a day per account (1,000 once the account has
bought $10 of credits), failed requests count, and calls are paced to 20 a minute. Plan your runs.

## Step 1: RAG, or the whole corpus in one prompt?

This corpus is small enough to fit in one prompt. Run the same five questions both ways, then compare
score, input tokens and latency:

```
lab compare
```

- Which approach answered more, and which cost more per question?
- How large would the corpus need to be before RAG wins on cost? On accuracy?

## Part 3: many sources

Targets the `multihop` and `aggregation` categories. Research these before you build:

- When does a question need more than one search, and how do you decide what to search for next?
- How would the Lab 1 tool loop use `search` as a tool, and what budget stops it?
- How do you follow a ticket's attachment, or an error code, to the document that explains it?
- Why can top-k retrieval never answer "what is the most common cause?", and what do map-reduce over
  documents and GraphRAG do instead?

## Part 4: trust

Targets `version`, `conflict`, `tenant`, `unanswerable` and `injection`. Research these before you
build:

- Which source wins when a policy page, a release note and a FAQ disagree, and how does the model
  know which is newer?
- Where must a merchant filter sit so one merchant's contract can never reach another?
- Why does a distance threshold fail on a question that is close to the corpus but not answered by
  it? What does a sufficient-context check do instead?
- How do provenance tags and an instruction hierarchy stop instructions hidden in a ticket?

If you make chunks larger, remember the embedding model reads only the first 256 tokens of each.

Each chunk carries `chunk.meta`: `type`, `product_version`, `updated`, `tenant` and `title`. Each
question carries `question["tenant"]`, a merchant ID or `None`. The controls (plain, identifier,
table, image) should not drop; if they do, your fix broke something.

## Build

Edit `MyCopilot` in `mylab/copilot.py`, then:

```
lab copilot --ids D03 D16 D20             a few questions, scored against the saved baseline
lab explain copilot D20                   what it retrieves, with each chunk's source details
lab explain copilot "refund window" --tenant M-GFB
lab rescore runs/mine_copilot_dev.jsonl
```

## Submit Parts 3 and 4

Run the test questions once, then hand in `submissions/<PARTICIPANT>_copilot_test.jsonl` with your
`mylab/` folder and your decision record:

```
lab submit copilot
```

## Decision record

Copy [decision-record.md](decision-record.md) and fill it in.
