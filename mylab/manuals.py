"""Parts 1 and 2: your manuals pipeline.

Run it with `lab manuals`, inspect one question with `lab explain manuals A01`, and read the
baseline you are extending in labkit/manuals.py.

A unit is a dict: unit_id, doc_id, page, type ("text", "figure", "table"), bbox [x0, y0, x1, y1]
in points, section, caption_text, artefact (what is returned) and search_text (what is embedded).
unit["page"] is None means the unit has no provenance. `hits` is a list of (unit, score).
"""
from labkit import llm  # noqa: F401  (llm.caption is used in story B)
from labkit.manuals import ManualsBaseline


class MyManuals(ManualsBaseline):
    name = "my-manuals"

    def select(self, units):
        # Story A: keep only the units that deserve to be indexed.
        return units

    def enrich(self, unit):
        # Story B: describe figures for search, e.g. llm.caption(unit["artefact"], "...").
        #          The image path is relative to data/manuals; llm.caption resolves it.
        # Story C (Part 2): table rows a search can match, with their headers.
        return super().enrich(unit)

    # Story D (Part 2): override build_index and retrieve to fuse BM25 with dense ranking.

    def answer(self, question, hits):
        # Story E: return the artefact the question asks for, with its citation.
        # Story F: abstain when no sourced unit covers the question:
        #   return {"answer_type": "none", "unit_id": None, "citation": None,
        #           "abstained": True, "reason": "..."}
        return super().answer(question, hits)
