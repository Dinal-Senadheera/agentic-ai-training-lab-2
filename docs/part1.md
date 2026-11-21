# Part 1 (in session): answer with the artefact

Aralia's field technicians install tills, printers, cash drawers and card readers. When they ask how
a cash drawer is wired, they want the wiring diagram and its page, not a paragraph about it. Ask
"show the rear panel of the Xprinter XP-Q80" and the answer is Figure 3 on page 3 of the field
service manual. Figure 2, on the same page, is the wrong printer.

**Retrieve by text, answer with the artefact:** search something textual, but hand back the original
figure or table, linked to its source.

- **Make figures and tables retrievable.** An image is found through a good description of it; a
  table through rows a query can match.
- **Carry provenance.** Every answer names its document and page. A unit with no page is never a
  sourced answer.
- **Fail closed.** A confident answer with the wrong figure is the worst outcome. When nothing
  sourced answers, abstain and say why.

The two manuals are already parsed into **units**: paragraphs, figures and tables. Each unit has its
provenance (`doc_id`, `page`, `bbox`), its `section` and printed `caption_text`, an `artefact` (what
is returned: the text, the image file, or the table's rows) and a `search_text` (what is embedded;
empty for figures and tables until you enrich them). The parser kept everything, including logos, an
icon, and a technician's photo that belongs to no document.

```
lab show fsm-fig3 fsm-tab3b
```

## Step 1: Measure the baseline by type

Read `ManualsBaseline` in `labkit/manuals.py`, then run it and read its scorecard:

```
lab manuals --pipeline baseline
lab explain manuals A01 --pipeline baseline
```

Compare **unit hit@5** with **page hit@5** for figures: page level counts a hit when anything from the
right page comes back, unit level only when the figure itself does. Write one sentence on what that
gap means for a technician.

## Step 2: Build, one story at a time

Edit `MyManuals` in `mylab/manuals.py`, then run `lab manuals`. It scores your pipeline against the
saved baseline run. Score after every story so each gain is attributable, and use
`lab explain manuals <ID>` to see why a question fails.

| Story | Method | Done when |
| --- | --- | --- |
| **A. Index only what deserves it.** Decide which units are real figures and which have provenance. | `select` | No logo or icon is indexed; no unit without a page can become an answer. |
| **B. Describe figures for search.** Caption each figure with `llm.caption(unit["artefact"], prompt)`. Write the prompt for search: device model, labels, part numbers, values. | `enrich` | Each figure's search text says what makes it different from its neighbours. Re-runs come from the cache. |
| **E. Answer with the artefact.** Decide whether the question wants a figure, a table or text, and return that unit with its citation. | `answer` | Figure and table questions return the real artefact and its page. |
| **F. Fail closed.** Abstain, with a `reason`, when no sourced unit covers the question. | `answer` | Both unanswerable dev questions abstain, and no answerable one does. |

Useful facts: search uses all-MiniLM-L6-v2, the embedding model from the primitives lab. It reads
only the first 256 tokens of a text, so a long caption is cut off: put what identifies the figure
first. Scores are cosine similarity (higher is closer); with normalised vectors this ranks the same
as L2 distance. `unit["bbox"]` is `[x0, y0, x1, y1]` in points; `unit["page"] is None` means no
provenance; `hits` is a list of `(unit, score)`. Captioning is the only step that costs model calls,
so caption only what needs it.

## Step 3: Submit Part 1

Before you submit, check that:

- [ ] Logos, icons and units without a page never become answers.
- [ ] Figures are captioned for search, and the captions come from the cache on re-runs.
- [ ] Figure and table answers return the real artefact and its page.
- [ ] The system abstains when nothing sourced answers.
- [ ] You can explain the unit and page gap from Step 1.

Run the test questions once, then hand `submissions/<PARTICIPANT>_manuals_test.jsonl` to your facilitator:

```
lab submit manuals
```
