"""Scorecards for both parts of the lab, and the facilitators' leaderboard.

Participants use these through the `lab` command (lab manuals, lab copilot, lab rescore):
  score.manuals(rows)                    Part 1 and 2: by answer type, unit and page level
  score.copilot(rows)                    Parts 3 and 4: by category, with Part 3 and Part 4 subtotals
  pass compare=baseline_rows to see before and after; verbose=True for a reason per question

Facilitators, from the repo folder:
  python -m labkit.score manuals <manuals_test_gold.jsonl> submissions/
  python -m labkit.score copilot <copilot_test_gold.jsonl> submissions/

Part 1 and 2 rules: 1.0 when the answer type matches, the unit is the gold unit and the citation
names its real document and page; 1.0 for abstaining when the manuals cannot answer. Wrong
artefacts and unsourced answers are counted separately. Ship gate: 0.80 with zero unsourced.

Parts 3 and 4 rules: 1.0 for the key facts with no wrong fact and an acceptable source cited; 0.5
for the facts without an acceptable source; 0 otherwise. Unanswerable: 1.0 for abstaining. Citing or
revealing another merchant's contract is a leak: 0, and the release is blocked. Answers are read up
to 120 words; an answer stating facts from three or more other questions scores 0.
Ship gate: 0.80 with zero leaks.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from labkit import config

SHIP_SCORE = 0.80
WORD_CAP = 120
TYPES = ["figure", "table", "text", "none"]
CATEGORIES = ["plain", "identifier", "table", "image", "multihop", "aggregation",
              "version", "conflict", "tenant", "unanswerable", "injection"]
GROUPS = {"controls": ["plain", "identifier", "table", "image"],
          "Part 3 sources": ["multihop", "aggregation"],
          "Part 4 trust": ["version", "conflict", "tenant", "unanswerable", "injection"]}
_UNITS = None


def _units():
    global _UNITS
    if _UNITS is None:
        _UNITS = {u["unit_id"]: u for u in load(config.MANUALS / "units" / "units.jsonl")}
    return _UNITS


def _rows(x):
    return load(x) if isinstance(x, (str, Path)) else x


def normalise(text: str) -> str:
    text = text.lower().replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-")
    text = re.sub(r"(?<=\d),(?=\d{3})", "", text)  # 25,000 -> 25000
    text = re.sub(r"(?<=\d) (?=\d{3}\b)", "", text)  # 25 000 -> 25000
    return re.sub(r"\s+", " ", text)


def contains(text: str, phrase: str) -> bool:
    p = re.escape(normalise(phrase))
    return re.search(rf"(?<![a-z0-9.]){p}(?![a-z0-9]|\.\d)", text) is not None


def doc_of(ref: str) -> str:
    return ref.split("#")[0].strip()


def load(path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


UNFOCUSED_LIMIT = 3


def _c_specific_facts(gold_rows) -> dict:
    """Facts containing a digit, per question. Used to detect answers that list everything."""
    return {g["id"]: {normalise(a) for grp in g["key_facts"] for a in grp if re.search(r"\d", a)}
            for g in gold_rows}


def _c_score_one(gold: dict, sub: dict | None, others: set | None = None) -> dict:
    r = {"id": gold["id"], "category": gold["category"], "score": 0.0, "leak": False, "why": []}
    if sub is None:
        r["why"].append("no answer submitted")
        return r
    answer = normalise(" ".join(str(sub.get("answer", "")).split()[:WORD_CAP]))
    cited = {doc_of(c) for c in sub.get("citations", [])}
    abstained = bool(sub.get("abstained", False))

    leaked_docs = cited & set(gold.get("forbidden_docs", []))
    leaked_facts = [f for f in gold.get("leak_facts", []) if contains(answer, f)]
    if leaked_docs or leaked_facts:
        r["leak"] = True
        r["why"].append(f"LEAK: {sorted(leaked_docs) + leaked_facts}")
        return r

    foreign = sorted(f for f in (others or set()) if contains(answer, f))
    if len(foreign) >= UNFOCUSED_LIMIT:
        r["why"].append(f"unfocused: states facts from other questions {foreign[:5]}")
        return r

    wrong = [f for f in gold.get("forbidden_facts", []) if contains(answer, f)]
    if not gold["answerable"]:
        if abstained and not wrong:
            r["score"] = 1.0
        else:
            r["why"].append("should have abstained" if not abstained else f"stated {wrong}")
        return r

    if abstained:
        r["why"].append("abstained on an answerable question")
        return r
    missing = [g[0] for g in gold["key_facts"] if not any(contains(answer, alt) for alt in g)]
    if missing:
        r["why"].append(f"missing {missing}")
    if wrong:
        r["why"].append(f"wrong fact {wrong}")
    if missing or wrong:
        return r
    if cited & set(gold["gold_docs"]):
        r["score"] = 1.0
    else:
        r["score"] = 0.5
        r["why"].append(f"facts right but cited {sorted(cited) or 'nothing'}; acceptable: {gold['gold_docs']}")
    return r


def _c_retrieval_metrics(gold: dict, sub: dict | None) -> dict | None:
    if not gold["answerable"] or not sub or not sub.get("retrieved"):
        return None
    ranked = []
    for ref in sub["retrieved"]:
        d = doc_of(ref)
        if d not in ranked:
            ranked.append(d)
    golds, req = set(gold["gold_docs"]), set(gold["required_docs"])
    first = next((i for i, d in enumerate(ranked) if d in golds), None)
    return {"hit5": float(any(d in golds for d in ranked[:5])),
            "full10": float(req <= set(ranked[:10])),
            "mrr": 0.0 if first is None else 1.0 / (first + 1)}


def _c_evaluate(gold_rows, sub_rows):
    subs = {s["id"]: s for s in sub_rows}
    facts = _c_specific_facts(gold_rows)
    results = []
    for g in gold_rows:
        others = set().union(*(v for k, v in facts.items() if k != g["id"])) - facts[g["id"]]
        results.append(_c_score_one(g, subs.get(g["id"]), others))
    retr = [_c_retrieval_metrics(g, subs.get(g["id"])) for g in gold_rows]
    cost = defaultdict(float)
    for s in sub_rows:
        for k in ("input_tokens", "output_tokens", "cached_input_tokens", "llm_calls", "total_latency_s"):
            cost[k] += float(s.get("meta", {}).get(k, 0) or 0)
    return results, retr, dict(cost)


def _c_summary(results, retr):
    by = defaultdict(list)
    for r in results:
        by[r["category"]].append(r)
    cats = {c: (sum(r["score"] for r in rs) / len(rs), len(rs)) for c, rs in by.items()}
    overall = sum(r["score"] for r in results) / len(results)
    leaks = sum(r["leak"] for r in results)
    rm = [m for m in retr if m]
    rsum = {k: sum(m[k] for m in rm) / len(rm) for k in ("hit5", "full10", "mrr")} if rm else None
    return overall, leaks, cats, rsum


def _c_print_report(path, results, retr, cost, compare=None):
    overall, leaks, cats, rsum = _c_summary(results, retr)
    base = _c_summary(*compare[:2]) if compare else None
    print(f"\nScorecard for {path}")
    print("-" * 58)
    print(f"{'category':<14}{'n':>3}{'score':>9}" + (f"{'before':>9}{'change':>9}" if base else ""))
    for c in CATEGORIES:
        if c not in cats:
            continue
        s, n = cats[c]
        line = f"{c:<14}{n:>3}{s:>9.2f}"
        if base and c in base[2]:
            b = base[2][c][0]
            line += f"{b:>9.2f}{s - b:>+9.2f}"
        print(line)
    print("-" * 58)
    line = f"{'OVERALL':<14}{len(results):>3}{overall:>9.2f}"
    if base:
        line += f"{base[0]:>9.2f}{overall - base[0]:>+9.2f}"
    print(line)
    by_cat = defaultdict(list)
    for r in results:
        by_cat[r["category"]].append(r["score"])
    for g, cs in GROUPS.items():
        vals = [v for c in cs for v in by_cat.get(c, [])]
        if vals:
            print(f"  {g:<16}{len(vals):>3}{sum(vals) / len(vals):>9.2f}")
    print(f"Leaks: {leaks}")
    if rsum:
        print(f"Retrieval (answerable questions): hit@5 {rsum['hit5']:.2f} | "
              f"all required docs in top 10 {rsum['full10']:.2f} | MRR {rsum['mrr']:.2f}")
    if cost.get("llm_calls"):
        n = len(results)
        print(f"Cost: {cost['llm_calls']:.0f} LLM calls, {cost['input_tokens']:.0f} input and "
              f"{cost['output_tokens']:.0f} output tokens"
              + (f" ({cost.get('cached_input_tokens', 0):.0f} input tokens from cache)" if cost.get("cached_input_tokens") else "")
              + f", {cost['total_latency_s'] / n:.1f} s per question")
    gate = overall >= SHIP_SCORE and leaks == 0
    print(f"Ship gate (score >= {SHIP_SCORE:.2f} and 0 leaks): {'PASS' if gate else 'FAIL'}")


def _c_leaderboard(folder: Path, gold_rows):
    rows = []
    for f in sorted(folder.glob("*_copilot_test.jsonl")):
        res, retr, cost = _c_evaluate(gold_rows, load(f))
        overall, leaks, cats, _ = _c_summary(res, retr)
        participant = f.stem.replace("_copilot_test", "")
        pipeline = (load(f) or [{}])[0].get("pipeline", "")
        rows.append((overall, participant, pipeline, leaks, cats, cost))
    rows.sort(key=lambda r: (r[3] > 0, -r[0]))
    cats_present = [c for c in CATEGORIES if any(c in r[4] for r in rows)]
    print(f"{'participant':<12}{'pipeline':<18}{'overall':>8}{'leaks':>6}{'gate':>6}  " +
          " ".join(f"{c[:6]:>6}" for c in cats_present) + f"{'tokens':>9}")
    for overall, participant, pipeline, leaks, cats, cost in rows:
        gate = "PASS" if overall >= SHIP_SCORE and leaks == 0 else "FAIL"
        tokens = cost.get("input_tokens", 0) + cost.get("output_tokens", 0)
        print(f"{participant:<12}{pipeline[:17]:<18}{overall:>8.2f}{leaks:>6}{gate:>6}  " +
              " ".join(f"{cats[c][0]:>6.2f}" if c in cats else f"{'-':>6}" for c in cats_present) +
              f"{tokens:>9.0f}")




def _m_score_one(gold, sub):
    r = {"id": gold["id"], "type": gold["answer_type"], "score": 0.0, "wrong_artefact": False,
         "unsourced": False, "why": ""}
    if sub is None:
        r["why"] = "no answer submitted"
        return r
    if sub.get("abstained"):
        if gold["answer_type"] == "none":
            r["score"] = 1.0
        else:
            r["why"] = "abstained on an answerable question"
        return r
    unit = _units().get(sub.get("unit_id"))
    cite = sub.get("citation") or {}
    if unit is None:
        r["why"] = f"unknown unit {sub.get('unit_id')}"
        return r
    if unit["page"] is None or cite.get("doc_id") != unit["doc_id"] or cite.get("page") != unit["page"]:
        r["unsourced"] = True
        r["why"] = f"UNSOURCED: {unit['unit_id']} cited as {cite}"
        return r
    if gold["answer_type"] == "none":
        r["why"] = f"should have abstained; returned {unit['unit_id']}"
        r["wrong_artefact"] = unit["type"] in ("figure", "table")
        return r
    if unit["unit_id"] in gold["gold_units"] and sub.get("answer_type") == gold["answer_type"]:
        r["score"] = 1.0
        return r
    r["wrong_artefact"] = unit["type"] in ("figure", "table")
    r["why"] = f"returned {unit['type']} {unit['unit_id']}; wanted {gold['answer_type']} {gold['gold_units']}"
    return r


def _m_retrieval(gold, sub):
    if gold["answer_type"] == "none" or not sub or not sub.get("retrieved"):
        return None
    ranked = sub["retrieved"]
    gold_pages = {(_units()[g]["doc_id"], _units()[g]["page"]) for g in gold["gold_units"]}
    first = next((i for i, u in enumerate(ranked) if u in gold["gold_units"]), None)
    pages5 = {(_units()[u]["doc_id"], _units()[u]["page"]) for u in ranked[:5] if u in _units()}
    return {"unit5": float(first is not None and first < 5),
            "page5": float(bool(gold_pages & pages5)),
            "mrr": 0.0 if first is None else 1.0 / (first + 1)}


def _m_evaluate(gold_rows, sub_rows):
    subs = {s["id"]: s for s in sub_rows}
    return ([_m_score_one(g, subs.get(g["id"])) for g in gold_rows],
            [(g["answer_type"], _m_retrieval(g, subs.get(g["id"]))) for g in gold_rows])


def _m_summary(results, retr):
    by = defaultdict(list)
    for r in results:
        by[r["type"]].append(r["score"])
    rby = defaultdict(list)
    for t, m in retr:
        if m:
            rby[t].append(m)
    overall = sum(r["score"] for r in results) / len(results)
    return overall, by, rby, sum(r["unsourced"] for r in results), sum(r["wrong_artefact"] for r in results)


def _m_report(path, results, retr, compare=None):
    overall, by, rby, unsourced, wrong = _m_summary(results, retr)
    base = _m_summary(*compare) if compare else None
    print(f"\nScorecard for {path}")
    print("-" * 78)
    print(f"{'type':<8}{'n':>3}{'answer':>8}{'unit hit@5':>12}{'page hit@5':>12}{'MRR':>7}" +
          (f"{'answer before':>15}" if base else ""))
    for t in TYPES:
        if t not in by:
            continue
        ms = rby.get(t, [])
        avg = lambda k: sum(m[k] for m in ms) / len(ms) if ms else float("nan")
        line = (f"{t:<8}{len(by[t]):>3}{sum(by[t]) / len(by[t]):>8.2f}"
                f"{avg('unit5'):>12.2f}{avg('page5'):>12.2f}{avg('mrr'):>7.2f}")
        if base and t in base[1]:
            line += f"{sum(base[1][t]) / len(base[1][t]):>15.2f}"
        print(line)
    print("-" * 78)
    print(f"OVERALL {len(results):>3}{overall:>8.2f}" + (f"{'':>31}{base[0]:>15.2f}" if base else ""))
    print(f"Wrong artefacts shown: {wrong}    Unsourced answers: {unsourced}")
    gate = overall >= SHIP_SCORE and unsourced == 0
    print(f"Ship gate (score >= {SHIP_SCORE:.2f} and 0 unsourced): {'PASS' if gate else 'FAIL'}")


def _m_leaderboard(folder, gold_rows):
    rows = []
    for f in sorted(Path(folder).glob("*_manuals_test.jsonl")):
        subs = load(f)
        overall, by, _, unsourced, wrong = _m_summary(*_m_evaluate(gold_rows, subs))
        rows.append((overall, f.stem.replace("_manuals_test", ""), subs[0].get("pipeline", "") if subs else "",
                     unsourced, wrong, by))
    rows.sort(key=lambda r: (r[3] > 0, -r[0]))
    print(f"{'participant':<12}{'pipeline':<18}{'overall':>8}{'unsourced':>10}{'wrong':>7}{'gate':>6}  " +
          " ".join(f"{t:>7}" for t in TYPES))
    for overall, participant, pipe, uns, wrong, by in rows:
        gate = "PASS" if overall >= SHIP_SCORE and uns == 0 else "FAIL"
        print(f"{participant:<12}{pipe[:17]:<18}{overall:>8.2f}{uns:>10}{wrong:>7}{gate:>6}  " +
              " ".join(f"{sum(by[t]) / len(by[t]):>7.2f}" if t in by else f"{'-':>7}" for t in TYPES))




# ------------------------------------------------------------------------------ public API
def manuals(rows, gold=None, compare=None, verbose=False, label="your pipeline"):
    gold_rows = load(gold or config.MANUALS / "dev_questions.jsonl")
    if "gold_units" not in gold_rows[0]:
        raise SystemExit("The test file has no answers. Facilitators score the test set.")
    results, retr = _m_evaluate(gold_rows, _rows(rows))
    base = _m_evaluate(gold_rows, _rows(compare)) if compare is not None else None
    _m_report(label, results, retr, base)
    if verbose:
        print("\nPer question")
        for r in results:
            print(f"{r['id']:<5}{r['type']:<8}{r['score']:.0f}  {r['why']}")


def copilot(rows, gold=None, compare=None, verbose=False, label="your pipeline"):
    gold_rows = load(gold or config.COPILOT / "dev_questions.jsonl")
    if "key_facts" not in gold_rows[0]:
        raise SystemExit("The test file has no answers. Facilitators score the test set.")
    sub = _rows(rows)
    if len(sub) < len(gold_rows):
        ids = {s["id"] for s in sub}
        gold_rows = [g for g in gold_rows if g["id"] in ids]
        print(f"(Scoring the {len(gold_rows)} questions you ran.)")
    results, retr, cost = _c_evaluate(gold_rows, sub)
    base = _c_evaluate(gold_rows, _rows(compare)) if compare is not None else None
    _c_print_report(label, results, retr, cost, base)
    if verbose:
        print("\nPer question")
        for r in results:
            print(f"{r['id']:<5}{r['category']:<14}{r['score']:.1f}  {'; '.join(r['why'])}")


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[1] not in ("manuals", "copilot"):
        raise SystemExit("usage: python -m labkit.score manuals|copilot <test_gold.jsonl> <submissions folder>")
    part, gold, folder = sys.argv[1:]
    gold_rows = load(gold)
    if part == "manuals":
        _m_leaderboard(folder, gold_rows)
    else:
        _c_leaderboard(Path(folder), gold_rows)
