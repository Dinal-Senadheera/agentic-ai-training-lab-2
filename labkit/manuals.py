"""Part 1: answering with the artefact from Aralia's hardware manuals.

A unit is one piece of a manual: text, figure or table, with its provenance:
  unit_id, doc_id, page, type, bbox, section, caption_text, artefact, search_text
  artefact     what is RETURNED: the paragraph, the figure's image path, or the table's header and rows
  search_text  what is EMBEDDED and searched; empty for figures and tables until enriched
"""
import json
import time

import numpy as np

from labkit import config, embed, llm


def load_units() -> list[dict]:
    with open(config.MANUALS / "units" / "units.jsonl", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def load_questions(split: str) -> list[dict]:
    with open(config.MANUALS / f"{split}_questions.jsonl", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


class ManualsBaseline:
    """Searches only what the parser produced, and returns the top hit whatever it is."""
    name = "baseline"

    def select(self, units):
        """Which units to index. Baseline: all of them, logos, icons and loose photos included."""
        return units

    def enrich(self, unit):
        """Search text. Figures: the printed caption. Tables: caption plus every cell, flattened."""
        if unit["type"] == "figure":
            return unit["caption_text"]
        if unit["type"] == "table":
            t = unit["artefact"]
            cells = [c for row in ([t["header"]] if t["header"] else []) + t["rows"] for c in row]
            return unit["caption_text"] + " " + " ".join(cells)
        return unit["search_text"]

    def build_index(self):
        self.units = self.select(load_units())
        for u in self.units:
            u["search_text"] = self.enrich(u)
        self.vectors = embed.embed_documents([u["search_text"] or " " for u in self.units])

    def retrieve(self, question, k=5):
        """Dense similarity only."""
        scores = self.vectors @ embed.embed_queries([question["question"]])[0]
        return [(self.units[i], float(scores[i])) for i in np.argsort(-scores)[:k]]

    def answer(self, question, hits):
        """The top hit, whatever its type, with whatever provenance it has."""
        top = hits[0][0]
        return {"answer_type": top["type"], "unit_id": top["unit_id"],
                "citation": {"doc_id": top["doc_id"], "page": top["page"]}, "abstained": False}

    def run(self, question):
        start = time.time()
        hits = self.retrieve(question)
        out = self.answer(question, hits)
        out["retrieved"] = [u["unit_id"] for u, _ in hits]
        out["meta"] = {"latency_s": round(time.time() - start, 3)}
        return {"id": question["id"]} | out


def run(pipe, split="dev", team=None, ids=None, quiet=False):
    """Index, answer every question in the split, and save the submission if a team is given."""
    before = dict(llm.USAGE)
    pipe.build_index()
    qs = [q for q in load_questions(split) if not ids or q["id"] in ids]
    rows = []
    for q in qs:
        row = pipe.run({"id": q["id"], "question": q["question"]})
        row["pipeline"] = pipe.name
        rows.append(row)
        if not quiet:
            what = "abstained" if row.get("abstained") else f"{row['answer_type']} {row['unit_id']} {row['citation']}"
            print(f"{q['id']}: {what}")
    calls = llm.USAGE["calls"] - before["calls"]
    cached = llm.USAGE["captions_from_cache"] - before["captions_from_cache"]
    print(f"{len(pipe.units)} units indexed. Model calls this run: {calls}; captions served from cache: {cached}.")
    if team:
        config.SUBMISSIONS.mkdir(exist_ok=True)
        path = config.SUBMISSIONS / f"{team}_manuals_{split}.jsonl"
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        print(f"Saved {path.name}")
    return rows


def show(unit_or_id):
    """Print a unit: its provenance, then the text, the table, or the path of the figure's image."""
    u = unit_or_id if isinstance(unit_or_id, dict) else {x["unit_id"]: x for x in load_units()}[unit_or_id]
    where = f"{u['doc_id']} p.{u['page']}" if u["page"] else "no page"
    print(f"{u['unit_id']} ({u['type']}, {where}, section: {u.get('section') or 'none'}) {u['caption_text']}")
    if u["type"] == "figure":
        print(f"  image: {config.MANUALS / u['artefact']}")
        if u.get("search_text"):
            print(f"  search text: {' '.join(u['search_text'].split())[:160]}")
    elif u["type"] == "table":
        t = u["artefact"]
        header = t["header"] or ["(no header)"] + [""] * (len(t["rows"][0]) - 1)
        rows = [header] + t["rows"]
        widths = [max(len(str(r[i])) for r in rows if i < len(r)) for i in range(len(header))]
        for n, r in enumerate(rows):
            print("  " + " | ".join(str(c).ljust(w) for c, w in zip(r, widths)))
            if n == 0:
                print("  " + "-+-".join("-" * w for w in widths))
    else:
        print("  " + u["artefact"])


def explain(pipe, question, k=5, show_answer=True):
    """What the pipeline retrieves for a question ID or any text, and what it would answer."""
    q = next((x for s in ("dev", "test") for x in load_questions(s) if x["id"] == question),
             {"id": "free", "question": question})
    hits = pipe.retrieve(q, k=k)
    print(f"[{pipe.name}] {q['question']}")
    for rank, (u, score) in enumerate(hits, 1):
        where = f"{u['doc_id']} p.{u['page']}" if u["page"] else "NO PAGE"
        text = " ".join((u["search_text"] or "(empty)").split())[:80]
        print(f" {rank}. {score:7.4f}  {u['type']:<6} {u['unit_id']:<16} {where:<25} {text}")
    a = pipe.answer(q, hits)
    if "gold_units" in q:
        print(f"    gold: {q['answer_type']} {q['gold_units']}")
    if a.get("abstained"):
        print(f" -> abstains: {a.get('reason', '')}")
    else:
        print(f" -> answers with {a['answer_type']} {a['unit_id']}")
        if show_answer:
            show(next(u for u in pipe.units if u["unit_id"] == a["unit_id"]))
