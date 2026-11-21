"""Check the lab's setup:  lab check (or python -m labkit.check)

1. The embedding model: loads it (downloading it the first time) and embeds three phrases. No API calls.
2. The language model: the configured provider and model, the key's limits and today's free-model
   allowance (OpenRouter), whether the model accepts images, then one text call and one image call.
"""
import json
import time
import urllib.request

from labkit import config, embed, llm

PHRASES = ["rear panel of the receipt printer", "printer rear panel connections", "refund policy for merchants"]


def check_embeddings():
    """True when the embedding model loads and ranks a related phrase above an unrelated one."""
    print(f"Embeddings: {config.EMBEDDING_BACKEND} / {config.EMBEDDING_MODEL}")
    if config.EMBEDDING_BACKEND == "stand-in":
        print("  stand-in backend: an offline keyword substitute for testing, not the lab's model.")
        return True
    start = time.time()
    try:
        v = embed._sentence_transformers(PHRASES)
    except Exception as e:
        print(f"  FAILED to load the embedding model: {str(e).splitlines()[0][:200]}\n"
              "  The first run downloads it from huggingface.co (about 90 MB). If your network blocks that\n"
              "  site, ask your facilitator for a copy of the model folder and set EMBEDDING_MODEL to its path.")
        return False
    related, unrelated = float(v[0] @ v[1]), float(v[0] @ v[2])
    ok = related > unrelated
    print(f"  loaded in {time.time() - start:.1f} s; {v.shape[1]} dimensions; similarity of related phrases "
          f"{related:.2f}, unrelated {unrelated:.2f}: {'OK' if ok else 'UNEXPECTED, check EMBEDDING_MODEL'}")
    return ok


def _get(url, key):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    return json.load(urllib.request.urlopen(req, timeout=30))


def main():
    embeddings_ok = check_embeddings()
    print(f"\nProvider: {config.LLM_PROVIDER}   Model: {config.model_name() or '(auto)'}")
    if config.LLM_PROVIDER == "openrouter":
        key = llm._require_key("OPENROUTER_API_KEY")
        info = _get("https://openrouter.ai/api/v1/key", key).get("data", {})
        print("\nKey:")
        for k in ("label", "is_free_tier", "limit", "limit_remaining", "usage", "usage_daily"):
            if k in info:
                print(f"  {k}: {info[k]}")
        daily = info.get("free_model_daily_requests")
        if isinstance(daily, dict):
            print(f"  free-model requests today (UTC): {daily.get('used')} used of {daily.get('limit')}, "
                  f"{daily.get('remaining')} left")
        print("  Free models allow 20 requests a minute, and 50 a day unless $10 or more of credits have")
        print("  ever been bought (then 1,000). More keys or accounts do not raise these limits.")
        models = _get("https://openrouter.ai/api/v1/models", key)["data"]
        by_id = {m["id"]: m for m in models}
        vision = llm.free_vision_models(models)
        print(f"\nFree models that accept images ({len(vision)}): " + ", ".join(vision[:8]))
        chosen = config.model_name() or llm.pick_openrouter_model()
        m = by_id.get(chosen)
        if not m:
            raise SystemExit(f"Model {chosen!r} is not on OpenRouter now. Set OPENROUTER_MODEL to one listed above.")
        images = "image" in (m.get("architecture") or {}).get("input_modalities", [])
        print(f"Using {chosen}: accepts images = {images}")
        if not images:
            print("  This model cannot read images. It works for Parts 3 and 4; Part 1 figure captions\n"
                  "  need an image model, so set OPENROUTER_MODEL to one listed above for Part 1.")
    else:
        images = True
    text, usage = llm.ask("Reply with one word.", "Say ready.")
    print(f"\nText call: {text.strip()!r} {usage}")
    if images:
        cap = llm.caption("artefacts/figures/fsm-fig3.png",
                          "Name the device model shown in this image, in a few words.")
        print(f"Image call: {cap.strip()[:120]!r}")
    else:
        print("Image call: skipped (text-only model)")
    print(f"\nRequests used by this check: {llm.USAGE['calls']}")
    if not embeddings_ok:
        raise SystemExit("The language model works, but the embedding model does not: see the message at the top.")


if __name__ == "__main__":
    main()
