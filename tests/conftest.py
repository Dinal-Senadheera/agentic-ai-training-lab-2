"""Offline test setup: a fake model and the lexical stand-in for embeddings, so no key or network is needed."""
import json
import os

os.environ["EMBEDDING_BACKEND"] = "stand-in"

import pytest  # noqa: E402

from labkit import config, llm  # noqa: E402

config.EMBEDDING_BACKEND = "stand-in"


@pytest.fixture(autouse=True)
def fake_model(monkeypatch, tmp_path):
    def _call(system, content, *args, **kwargs):
        if system.startswith("You describe images"):
            text = "A labelled device diagram."
        else:
            text = json.dumps({"answer": "mock", "citations": [], "abstained": False})
        return text, llm._record(len(str(content)) // 4, 10)

    monkeypatch.setattr(llm, "_call", _call)
    monkeypatch.setattr(config, "CACHE", tmp_path / "cache")
    monkeypatch.setattr(config, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(config, "SUBMISSIONS", tmp_path / "submissions")
    monkeypatch.setattr(config, "LLM_PROVIDER", "anthropic")
