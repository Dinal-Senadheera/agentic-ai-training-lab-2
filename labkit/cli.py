"""Command line for Agentic AI Training Lab 2. Run `lab --help` (or `python -m labkit --help`).

  lab check                              key, limits, model, one text and one image call
  lab show fsm-fig3 fsm-tab3b            print units: provenance, text, table or image path
  lab manuals                            run and score your Part 1 and 2 pipeline on dev
  lab manuals --pipeline baseline        the same for the baseline
  lab explain manuals A01                what a pipeline retrieves and answers for one question
  lab copilot --ids D03 D16              run and score your Part 3 and 4 pipeline on some dev questions
  lab compare                            whole corpus in one prompt against RAG, on five questions
  lab explain copilot D20                what the copilot retrieves, with each chunk's source details
  lab rescore runs/mine_copilot_dev.jsonl    score a saved run again, with no model calls
  lab submit manuals                     run the test questions once and write your submission
"""
import argparse
import importlib
import json
import sys

from labkit import config, copilot, llm, manuals, score

PIPELINES = {
    "manuals": {"baseline": "labkit.manuals:ManualsBaseline", "mine": "mylab.manuals:MyManuals"},
    "copilot": {"baseline": "labkit.copilot:CopilotBaseline", "mine": "mylab.copilot:MyCopilot",
                "whole": "labkit.copilot:WholeCorpusPipeline"},
}
FIVE = ["D03", "D09", "D16", "D21", "D23"]


def load_pipeline(part, name):
    """`baseline`, `mine`, `whole`, or any `module:Class`."""
    spec = PIPELINES[part].get(name, name)
    if ":" not in spec:
        raise SystemExit(f"Unknown pipeline {name!r}. Use {', '.join(PIPELINES[part])} or module:Class.")
    module, cls = spec.split(":")
    if str(config.ROOT) not in sys.path:
        sys.path.insert(0, str(config.ROOT))
    return getattr(importlib.import_module(module), cls)()


def rel(path):
    try:
        return path.relative_to(config.ROOT)
    except ValueError:
        return path


def save_run(rows, part, pipeline, split):
    config.RUNS.mkdir(exist_ok=True)
    path = config.RUNS / f"{pipeline}_{part}_{split}.jsonl"
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return path


def saved_run(part, pipeline, split="dev"):
    path = config.RUNS / f"{pipeline}_{part}_{split}.jsonl"
    return score.load(path) if path.exists() else None


def calls_note(before):
    print(f"Model calls this command: {llm.USAGE['calls'] - before}")


# ------------------------------------------------------------------------------ commands
def cmd_check(args):
    from labkit import check
    check.main()


def cmd_show(args):
    for unit_id in args.unit_ids:
        manuals.show(unit_id)
        print()


def cmd_part(args):
    """lab manuals / lab copilot: run a pipeline on dev, save the run, and score it."""
    part, before = args.part, llm.USAGE["calls"]
    pipe = load_pipeline(part, args.pipeline)
    if part == "manuals":
        rows = manuals.run(pipe, "dev", ids=args.ids, quiet=not args.answers)
    else:
        rows = copilot.run(pipe, "dev", ids=args.ids, retrieval_only=args.retrieval_only,
                           quiet=not args.answers)
    path = save_run(rows, part, args.pipeline.replace(":", "."), "dev")
    print(f"Run saved to {rel(path)}")
    compare = None
    if args.pipeline != "baseline" and not args.no_compare:
        compare = saved_run(part, "baseline")
        if compare is None:
            print("(No saved baseline run to compare with. Run `lab", part, "--pipeline baseline` once.)")
    scorer = score.manuals if part == "manuals" else score.copilot
    scorer(rows, compare=compare, verbose=not args.brief, label=pipe.name)
    calls_note(before)


def cmd_explain(args):
    pipe = load_pipeline(args.part, args.pipeline)
    pipe.build_index()
    question = " ".join(args.question)
    if args.part == "manuals":
        manuals.explain(pipe, question)
    else:
        copilot.explain(pipe, question, tenant=args.tenant)


def cmd_compare(args):
    """Whole corpus in one prompt against RAG, on the same questions."""
    before, ids = llm.USAGE["calls"], args.ids or FIVE
    whole = copilot.run(load_pipeline("copilot", "whole"), "dev", ids=ids, quiet=True)
    save_run(whole, "copilot", "whole", "dev")
    score.copilot(whole, label="whole corpus in one prompt")
    rag = saved_run("copilot", args.against)
    if rag is None or not {r["id"] for r in rag} >= set(ids):
        rag = copilot.run(load_pipeline("copilot", args.against), "dev", ids=ids, quiet=True)
    score.copilot([r for r in rag if r["id"] in ids], label=f"RAG ({args.against})")
    calls_note(before)


def cmd_rescore(args):
    rows = score.load(args.run)
    part = "manuals" if rows and "answer_type" in rows[0] else "copilot"
    compare = score.load(args.compare) if args.compare else None
    (score.manuals if part == "manuals" else score.copilot)(rows, compare=compare, verbose=True,
                                                           label=args.run)


def cmd_submit(args):
    participant = args.participant or config.PARTICIPANT
    if not participant.isalnum():
        raise SystemExit("Set PARTICIPANT in .env (or pass --participant) to your ID: letters and digits only.")
    out = config.SUBMISSIONS / f"{participant}_{args.part}_test.jsonl"
    if out.exists() and not args.force:
        raise SystemExit(f"{out.name} already exists. Each test split is run once; use --force to replace it.")
    before = llm.USAGE["calls"]
    pipe = load_pipeline(args.part, args.pipeline)
    (manuals.run if args.part == "manuals" else copilot.run)(pipe, "test", participant=participant, quiet=True)
    print(f"Hand {rel(out)} to your facilitator.")
    calls_note(before)


# ------------------------------------------------------------------------------ parser
def main(argv=None):
    ap = argparse.ArgumentParser(prog="lab", description="Agentic AI Training Lab 2 commands.",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="check the key, limits and model").set_defaults(func=cmd_check)

    p = sub.add_parser("show", help="print manual units")
    p.add_argument("unit_ids", nargs="+")
    p.set_defaults(func=cmd_show)

    for part in ("manuals", "copilot"):
        p = sub.add_parser(part, help=f"run and score a {part} pipeline on the dev questions")
        p.add_argument("--pipeline", default="mine", help="mine (default), baseline, or module:Class")
        p.add_argument("--ids", nargs="*", help="only these question IDs")
        p.add_argument("--answers", action="store_true", help="print each answer as it runs")
        p.add_argument("--brief", action="store_true", help="scorecard only, no per-question lines")
        p.add_argument("--no-compare", action="store_true", help="do not compare with the saved baseline")
        if part == "copilot":
            p.add_argument("--retrieval-only", action="store_true",
                           help="retrieve without answering: no model calls, retrieval metrics only")
        p.set_defaults(func=cmd_part, part=part)

    p = sub.add_parser("explain", help="what a pipeline retrieves and answers for one question")
    p.add_argument("part", choices=["manuals", "copilot"])
    p.add_argument("question", nargs="+", help="a question ID such as A01, or any question text")
    p.add_argument("--pipeline", default="mine")
    p.add_argument("--tenant", help="copilot only: merchant ID for free-text questions, e.g. M-GFB")
    p.set_defaults(func=cmd_explain)

    p = sub.add_parser("compare", help="whole corpus in one prompt against RAG")
    p.add_argument("--ids", nargs="*", help=f"question IDs (default {' '.join(FIVE)})")
    p.add_argument("--against", default="baseline", help="RAG pipeline to compare: baseline or mine")
    p.set_defaults(func=cmd_compare)

    p = sub.add_parser("rescore", help="score a saved run again, with no model calls")
    p.add_argument("run")
    p.add_argument("--compare", help="another saved run to compare with")
    p.set_defaults(func=cmd_rescore)

    p = sub.add_parser("submit", help="run the test questions once and write your submission")
    p.add_argument("part", choices=["manuals", "copilot"])
    p.add_argument("--pipeline", default="mine")
    p.add_argument("--participant")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_submit)

    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
