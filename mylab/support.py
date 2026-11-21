"""Parts 3 and 4: your support assistant.

Run it with `lab support --ids D03 D16` while developing, inspect one question with
`lab explain support D20`, and read the baseline you are extending in labkit/support.py.

Each chunk is a labkit.support.Chunk with chunk_id, doc_id, text and meta: type, product_version,
updated, tenant and title. Each question is a dict with id, question and tenant (a merchant ID or
None). `hits` is a list of (chunk, score).
"""
from labkit import llm  # noqa: F401
from labkit.support import Chunk, SupportBaseline, tokens  # noqa: F401


class MySupport(SupportBaseline):
    name = "my-support"

    # def chunk(self, docs):
    #     ...   e.g. put each source's type, version, date and merchant into its chunks

    # def retrieve(self, question, k=None):
    #     ...   Part 4: which chunks may this merchant and this product version see?
    #           Part 3: does the question need one search, several, or every ticket?

    # def answer(self, question, hits):
    #     ...   Part 3: search again for a second hop, within a step budget
    #           Part 4: is the context sufficient? Treat ticket text as data, not instructions.
    #     return {"answer": ..., "citations": [...], "abstained": ..., "meta": usage}
