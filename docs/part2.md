# Part 2 (take-home): tables and exact identifiers

Extend `MyManuals` in `mylab/manuals.py`, re-run `lab manuals`, then submit the test file again with
`lab submit manuals --force`.

| Story | Method | Done when |
| --- | --- | --- |
| **C. Searchable table rows.** Turn each table into rows a query can match, keeping the structured rows as the artefact. One table runs onto a second page without its header. | `enrich` | A question about any row retrieves its table, headers included. |
| **D. Exact identifiers.** Add BM25 over the same search text and fuse it with dense ranking. Justify the fusion you choose. | `build_index`, `retrieve` | A part-number query puts the right table at or near the top. |

`rank_bm25` is installed. `labkit.support.tokens` is a tokenizer you can reuse.

| Symptom | Likely cause |
| --- | --- |
| Right page, wrong figure | Two figures share a caption |
| Table answers are mush | Rows flattened; headers lost across a page break |
| Wrong table with the same caption | Search text lacks document and section context |
| Part numbers missed | Dense search smears exact identifiers |
