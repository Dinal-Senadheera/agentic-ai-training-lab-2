"""Parts 3 and 4: the Aralia support copilot.

The baseline already does a first RAG build well: chunking, dense embeddings fused with BM25
(reciprocal rank fusion) and a grounded prompt. Images and the plans table arrive as enriched text.
It does not reason about the sources it finds: their dates, versions, merchant, or trustworthiness.
"""
import json
import re
import time
from dataclasses import dataclass, field

import numpy as np
from rank_bm25 import BM25Okapi

from labkit import config, embed, llm

SYSTEM = (
    "You are a support copilot for Aralia Systems. Answer the support agent's question using only "
    "the context passages, and cite the chunk IDs you used. If the context does not contain the "
    "answer, set abstained to true. Reply with JSON only, in this form:\n"
    '{"answer": "<short answer>", "citations": ["<chunk_id>", ...], "abstained": false}'
)


@dataclass
class Chunk:
    chunk_id: str          # "<doc_id>#<n>", the form used in citations
    doc_id: str
    text: str
    meta: dict = field(default_factory=dict)   # title, type, product_version, updated, tenant, ...


def tokens(text):
    return re.findall(r"[a-z0-9](?:[a-z0-9\-\.]*[a-z0-9])?", text.lower())


def load_questions(split):
    with open(config.COPILOT / f"{split}_questions.jsonl", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def load_documents():
    """(doc_id, text, metadata) for every document, using enriched text for images and the PDF table."""
    corpus = config.COPILOT / "corpus"
    docs = []
    for e in json.loads((corpus / "manifest.json").read_text(encoding="utf-8")):
        enriched = (corpus / e["enriched"]).read_text(encoding="utf-8") if e.get("enriched") else ""
        if e["format"] == "markdown":
            raw = (corpus / e["path"]).read_text(encoding="utf-8")
            text = raw[raw.find("\n---", 3) + 4:].lstrip() if raw.startswith("---") else raw
        elif e["format"] == "pdf":
            from pypdf import PdfReader
            text = "\n".join(p.extract_text() or "" for p in PdfReader(str(corpus / e["path"])).pages)
            text += "\n\n" + enriched
        else:
            text = enriched
        if text.strip():
            docs.append((e["doc_id"], text, e))
    return docs


class CopilotBaseline:
    name = "baseline"
    chunk_size, overlap, top_k = 800, 100, 5

    def chunk(self, docs):
        """Fixed-size character windows; metadata kept on each chunk but not used."""
        out = []
        for doc_id, text, meta in docs:
            for n, start in enumerate(range(0, len(text), self.chunk_size - self.overlap)):
                piece = text[start:start + self.chunk_size]
                if piece.strip():
                    out.append(Chunk(f"{doc_id}#{n}", doc_id, piece, meta))
        return out

    def build_index(self):
        self.chunks = self.chunk(load_documents())
        self.vectors = embed.embed_documents([c.text for c in self.chunks])
        self.bm25 = BM25Okapi([tokens(c.text) for c in self.chunks])

    def retrieve(self, question, k=None):
        """Dense and BM25 rankings fused with reciprocal rank fusion. Ignores tenant, version and dates."""
        k = k or self.top_k
        dense = self.vectors @ embed.embed_queries([question["question"]])[0]
        sparse = self.bm25.get_scores(tokens(question["question"]))
        fused = np.zeros(len(self.chunks))
        for scores in (dense, sparse):
            for rank, i in enumerate(np.argsort(-scores)):
                fused[i] += 1.0 / (60 + rank)
        return [(self.chunks[i], float(fused[i])) for i in np.argsort(-fused)[:k]]

    def answer(self, question, hits):
        context = "\n\n".join(f"[{c.chunk_id}]\n{c.text}" for c, _ in hits)
        text, usage = llm.ask(SYSTEM, f"Context:\n{context}\n\nQuestion: {question['question']}")
        data = llm.parse_json(text)
        return {"answer": str(data.get("answer", text.strip())), "citations": [str(c) for c in data.get("citations", [])],
                "abstained": bool(data.get("abstained", False)), "meta": usage}

    def run(self, question, retrieval_only=False):
        start = time.time()
        hits = self.retrieve(question)
        out = ({"answer": "", "citations": [], "abstained": False, "meta": {}} if retrieval_only
               else self.answer(question, hits))
        out["retrieved"] = [c.chunk_id for c, _ in hits]
        out["meta"]["total_latency_s"] = round(time.time() - start, 2)
        return {"id": question["id"]} | out


class WholeCorpusPipeline(CopilotBaseline):
    """No retrieval: every document goes into one long prompt, cached between questions where the
    provider supports it. Compare its score, tokens and latency with RAG."""
    name = "whole-corpus"

    def build_index(self):
        self.chunks = self.chunk(load_documents())
        corpus = "\n\n".join(f"[{c.chunk_id}]\n{c.text}" for c in self.chunks)
        self.system = SYSTEM + "\n\nContext passages:\n" + corpus

    def retrieve(self, question, k=None):
        return [(c, 0.0) for c in self.chunks]

    def answer(self, question, hits):
        text, usage = llm.ask(self.system, f"Question: {question['question']}", cache_system=True)
        data = llm.parse_json(text)
        return {"answer": str(data.get("answer", text.strip())), "citations": [str(c) for c in data.get("citations", [])],
                "abstained": bool(data.get("abstained", False)), "meta": usage}

    def run(self, question, retrieval_only=False):
        row = super().run(question, retrieval_only)
        row["retrieved"] = []
        return row


def run(pipe, split="dev", team=None, ids=None, retrieval_only=False, quiet=False):
    """Index, answer each question, and save the submission if a team is given."""
    pipe.build_index()
    rows = []
    for q in load_questions(split):
        if ids and q["id"] not in ids:
            continue
        row = pipe.run({k: q.get(k) for k in ("id", "question", "tenant")}, retrieval_only)
        row["pipeline"] = pipe.name
        rows.append(row)
        if not quiet:
            print(f"{q['id']}: {'(abstained) ' if row['abstained'] else ''}{row['answer'][:90]!r}")
    if team:
        config.SUBMISSIONS.mkdir(exist_ok=True)
        path = config.SUBMISSIONS / f"{team}_copilot_{split}.jsonl"
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        print(f"Saved {path.name}")
    return rows


def explain(pipe, question, tenant=None, k=5):
    """What the pipeline retrieves for a question ID or any text, with each chunk's source details."""
    q = next((x for s in ("dev", "test") for x in load_questions(s) if x["id"] == question),
             {"id": "free", "question": question, "tenant": tenant})
    print(f"[{pipe.name}] {q['question']}   (merchant: {q.get('tenant') or 'none'})")
    for rank, (c, score) in enumerate(pipe.retrieve({k_: q.get(k_) for k_ in ("id", "question", "tenant")}, k=k), 1):
        m = c.meta
        src = f"{m['type']}, {m['product_version']}, {m['updated']}" + (f", {m['tenant']}" if m["tenant"] != "none" else "")
        print(f" {rank}. {score:7.4f}  {c.chunk_id:<30} [{src}]\n             {' '.join(c.text.split())[:80]}")
    if "gold_docs" in q:
        print(f"    acceptable sources: {q['gold_docs']}"
              + (f"   must not use: {q['forbidden_docs']}" if q.get("forbidden_docs") else ""))
