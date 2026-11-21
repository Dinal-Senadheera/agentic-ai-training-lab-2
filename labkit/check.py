"""Check the lab's model setup:  lab check (or python -m labkit.check)

Prints the configured provider and model, the key's limits and today's free-model allowance
(OpenRouter), whether the model accepts images, and makes one text call and one image call.
"""
import json
import urllib.request

from labkit import config, llm


def _get(url, key):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    return json.load(urllib.request.urlopen(req, timeout=30))


def free_vision_models(models):
    return [m["id"] for m in models
            if m["id"].endswith(":free") and "image" in (m.get("architecture") or {}).get("input_modalities", [])]


def main():
    print(f"Provider: {config.LLM_PROVIDER}   Model: {config.model_name() or '(auto)'}")
    if config.LLM_PROVIDER == "openrouter":
        key = config.setting("OPENROUTER_API_KEY")
        if not key:
            raise SystemExit("Set OPENROUTER_API_KEY in .env.")
        info = _get("https://openrouter.ai/api/v1/key", key).get("data", {})
        print("\nKey:")
        for k in ("label", "is_free_tier", "limit", "limit_remaining", "usage", "usage_daily"):
            if k in info:
                print(f"  {k}: {info[k]}")
        for k, v in info.items():
            if "free" in k.lower() and k != "is_free_tier":
                print(f"  {k}: {v}")
        print("  Free models allow 20 requests a minute, and 50 a day per account unless the account has")
        print("  bought $10 or more of credits (then 1,000). Failed requests count.")
        models = _get("https://openrouter.ai/api/v1/models", key)["data"]
        by_id = {m["id"]: m for m in models}
        vision = free_vision_models(models)
        print(f"\nFree models that accept images ({len(vision)}): " + ", ".join(vision[:8]))
        chosen = config.model_name() or llm.pick_openrouter_model()
        m = by_id.get(chosen)
        if not m:
            raise SystemExit(f"Model {chosen!r} is not on OpenRouter now. Set OPENROUTER_MODEL to one listed above.")
        images = "image" in (m.get("architecture") or {}).get("input_modalities", [])
        print(f"Using {chosen}: accepts images = {images}")
        if not images:
            print("  Figure captions need an image model: set OPENROUTER_MODEL to one listed above.")
    text, usage = llm.ask("Reply with one word.", "Say ready.")
    print(f"\nText call: {text.strip()!r} {usage}")
    cap = llm.caption("artefacts/figures/fsm-fig3.png", "Name the device model shown in this image, in a few words.")
    print(f"Image call: {cap.strip()[:120]!r}")
    print(f"\nRequests used by this check: {llm.USAGE['calls']}")


if __name__ == "__main__":
    main()
