"""One interface to the language model, whichever provider is configured.

  ask(system, user)                 -> (text, usage)
  caption(image_path, prompt)       -> text, cached on disk so re-runs cost nothing
  USAGE                             running totals for this session
"""
import base64
import hashlib
import json
import mimetypes
import time
from pathlib import Path

from labkit import config

USAGE = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cached_input_tokens": 0,
         "captions_from_cache": 0}
_client = None
_last_call = [0.0]
FREE_MODEL_GAP_S = 3.2      # stays under OpenRouter's 20 free-model requests a minute


def pick_openrouter_model():
    """The configured OpenRouter model, or the first free model that accepts images."""
    if config.OPENROUTER_MODEL:
        return config.OPENROUTER_MODEL
    import urllib.request
    req = urllib.request.Request("https://openrouter.ai/api/v1/models")
    models = json.load(urllib.request.urlopen(req, timeout=30))["data"]
    vision = [m["id"] for m in models if m["id"].endswith(":free")
              and "image" in (m.get("architecture") or {}).get("input_modalities", [])]
    if not vision:
        raise RuntimeError("No free OpenRouter model accepts images today. Set OPENROUTER_MODEL in .env.")
    config.OPENROUTER_MODEL = vision[0]
    print(f"Using OpenRouter model {vision[0]} (set OPENROUTER_MODEL in .env to choose another).")
    return vision[0]


def _require_key(name):
    """The API key, or a clear stop. The lab needs a key for every model call."""
    key = config.setting(name).strip()
    if not key or "your-key" in key:
        raise SystemExit(
            f"No API key: set {name} in .env. This lab needs an Anthropic or OpenRouter API key for every "
            "model call (figure captions and copilot answers). See 'API key' in the README.")
    return key


def _get_client():
    global _client
    if _client is None:
        if config.LLM_PROVIDER == "anthropic":
            import anthropic
            _client = anthropic.Anthropic(api_key=_require_key("ANTHROPIC_API_KEY"))
        elif config.LLM_PROVIDER == "openrouter":
            from openai import OpenAI
            key = _require_key("OPENROUTER_API_KEY")
            _client = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
        else:
            raise RuntimeError(f"Unknown LLM_PROVIDER {config.LLM_PROVIDER!r}: use anthropic or openrouter.")
    return _client


def _record(input_tokens, output_tokens, cached=0):
    USAGE["calls"] += 1
    USAGE["input_tokens"] += input_tokens or 0
    USAGE["output_tokens"] += output_tokens or 0
    USAGE["cached_input_tokens"] += cached or 0
    return {"llm_calls": 1, "input_tokens": input_tokens or 0, "output_tokens": output_tokens or 0,
            "cached_input_tokens": cached or 0}


def _call(system, content_anthropic, content_openai, max_tokens, cache_system, retries=3):
    client = _get_client()
    for attempt in range(retries):
        try:
            if config.LLM_PROVIDER == "anthropic":
                sys_block = [{"type": "text", "text": system}]
                if cache_system:
                    sys_block[0]["cache_control"] = {"type": "ephemeral"}
                r = client.messages.create(model=config.ANTHROPIC_MODEL, max_tokens=max_tokens, system=sys_block,
                                           messages=[{"role": "user", "content": content_anthropic}])
                text = "".join(b.text for b in r.content if b.type == "text")
                u = r.usage
                cached = getattr(u, "cache_read_input_tokens", 0) or 0
                created = getattr(u, "cache_creation_input_tokens", 0) or 0
                return text, _record(u.input_tokens + cached + created, u.output_tokens, cached)
            model = pick_openrouter_model()
            if model.endswith(":free"):
                wait = FREE_MODEL_GAP_S - (time.time() - _last_call[0])
                if wait > 0:
                    time.sleep(wait)
                _last_call[0] = time.time()
            r = client.chat.completions.create(
                model=model, max_tokens=max_tokens, temperature=0,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": content_openai}])
            u = r.usage
            return r.choices[0].message.content or "", _record(getattr(u, "prompt_tokens", 0),
                                                               getattr(u, "completion_tokens", 0))
        except Exception as e:
            if ("429" in str(e) or "rate" in str(e).lower()) and attempt < retries - 1:
                print("Rate limited; waiting 20 s ...")
                time.sleep(20)
                continue
            raise


def ask(system: str, user: str, max_tokens: int = 400, cache_system: bool = False):
    """One call. cache_system=True asks the provider to cache a long system prompt (Anthropic)."""
    start = time.time()
    text, usage = _call(system, user, user, max_tokens, cache_system)
    usage["latency_s"] = round(time.time() - start, 2)
    return text, usage


def caption(image_path, prompt: str, max_tokens: int = 500) -> str:
    """The model's description of an image, for a given prompt. Cached per image, prompt and model."""
    path = Path(image_path)
    if not path.is_absolute():
        path = config.MANUALS / path
    data = path.read_bytes()
    model = config.ANTHROPIC_MODEL if config.LLM_PROVIDER == "anthropic" else pick_openrouter_model()
    key = hashlib.sha1(data + prompt.encode() + model.encode()).hexdigest()
    cache_file = config.CACHE / "captions.json"
    cache = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}
    if key in cache:
        USAGE["captions_from_cache"] += 1
        return cache[key]
    media = mimetypes.guess_type(path.name)[0] or "image/png"
    b64 = base64.standard_b64encode(data).decode()
    anthropic_content = [{"type": "image", "source": {"type": "base64", "media_type": media, "data": b64}},
                         {"type": "text", "text": prompt}]
    openai_content = [{"type": "text", "text": prompt},
                      {"type": "image_url", "image_url": {"url": f"data:{media};base64,{b64}"}}]
    text, _ = _call("You describe images precisely.", anthropic_content, openai_content, max_tokens, False)
    cache[key] = text
    config.CACHE.mkdir(exist_ok=True)
    cache_file.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    return text


def parse_json(text: str) -> dict:
    """Pull the first JSON object out of a model reply."""
    import re
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        return json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        return {}
