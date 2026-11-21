"""Optional for Part 4: the copilot's chunks in a Chroma vector database, searchable with metadata filters.

The baseline keeps its vectors in a numpy array and searches all of them. A vector database can also
filter on each chunk's metadata during the search. Use it to test where a filter must sit:

    from labkit.vectorstore import ChromaStore
    store = ChromaStore(self.chunks)                      # in build_index, after chunking
    hits = store.search("refund window", k=8)             # no filter
    hits = store.search("refund window", k=8, where={"type": "policy"})
    hits = store.search("...", where={"$and": [{"type": "manual"}, {"updated_num": {"$gte": 20250101}}]})

Each result is (chunk, similarity), as in the baseline. Filterable metadata: doc_id, title, type,
product_version, tenant ("none" or a merchant ID), updated ("YYYY-MM-DD") and updated_num (YYYYMMDD
as a number, for $gt, $gte, $lt, $lte). Filter operators: $eq, $ne, $in, $nin, $and, $or.
Chroma runs in memory here, inside your Python process: no server, nothing saved to disk.
"""
import uuid

from labkit import embed

FIELDS = ("doc_id", "title", "type", "product_version", "tenant", "updated")


def _metadata(chunk):
    meta = {f: str(chunk.meta.get(f, "")) for f in FIELDS}
    meta["updated_num"] = int(meta["updated"].replace("-", "") or 0)
    return meta


class ChromaStore:
    def __init__(self, chunks):
        try:
            import chromadb
        except ImportError as e:
            raise SystemExit('Chroma is not installed: pip install -e ".[vectordb]"') from e
        self.by_id = {c.chunk_id: c for c in chunks}
        client = chromadb.EphemeralClient()
        self.collection = client.create_collection(
            f"aralia-{uuid.uuid4().hex[:8]}", embedding_function=None,
            configuration={"hnsw": {"space": "cosine"}})
        vectors = embed.embed_documents([c.text for c in chunks])
        self.collection.add(ids=[c.chunk_id for c in chunks], embeddings=vectors.tolist(),
                            metadatas=[_metadata(c) for c in chunks], documents=[c.text for c in chunks])

    def search(self, text, k=8, where=None):
        """The k most similar chunks that match `where`, as (chunk, similarity), best first."""
        query = embed.embed_queries([text])[0]
        r = self.collection.query(query_embeddings=[query.tolist()], n_results=k, where=where)
        return [(self.by_id[i], 1.0 - d) for i, d in zip(r["ids"][0], r["distances"][0])]
