"""Smoke tests: every command runs end to end offline. Run with `pytest`."""
import pytest

from labkit import cli, config, copilot, llm, manuals, score


def lab(*argv):
    cli.main(list(argv))


def test_units_and_questions_load():
    units = manuals.load_units()
    assert {u["type"] for u in units} == {"text", "figure", "table"}
    assert manuals.load_questions("dev") and copilot.load_questions("dev")
    assert "gold_units" not in manuals.load_questions("test")[0]
    assert "key_facts" not in copilot.load_questions("test")[0]


def test_show(capsys):
    lab("show", "fsm-fig3", "fsm-tab3b")
    out = capsys.readouterr().out
    assert "fsm-fig3" in out and "image:" in out and "fsm-tab3b" in out


@pytest.mark.parametrize("pipeline", ["baseline", "mine"])
def test_manuals_run_and_score(pipeline, capsys):
    lab("manuals", "--pipeline", pipeline, "--brief")
    out = capsys.readouterr().out
    assert "Ship gate" in out
    assert (config.RUNS / f"{pipeline}_manuals_dev.jsonl").exists()


def test_manuals_compare_with_saved_baseline(capsys):
    lab("manuals", "--pipeline", "baseline", "--brief")
    lab("manuals", "--brief")
    assert "before" in capsys.readouterr().out


def test_explain(capsys):
    lab("explain", "manuals", "A01")
    lab("explain", "manuals", "rear", "panel", "of", "the", "printer")
    lab("explain", "copilot", "D20")
    lab("explain", "copilot", "refund window", "--tenant", "M-GFB")
    assert capsys.readouterr().out.count("[") >= 4


def test_copilot_subset_and_retrieval_only(capsys):
    before = llm.USAGE["calls"]
    lab("copilot", "--pipeline", "baseline", "--ids", "D03", "D16", "--brief")
    assert llm.USAGE["calls"] - before == 2
    before = llm.USAGE["calls"]
    lab("copilot", "--retrieval-only", "--brief")
    assert llm.USAGE["calls"] == before
    assert "Ship gate" in capsys.readouterr().out


def test_compare(capsys):
    lab("compare", "--ids", "D03", "D09")
    out = capsys.readouterr().out
    assert "whole corpus" in out and "RAG" in out


def test_rescore(capsys):
    lab("manuals", "--pipeline", "baseline", "--brief")
    lab("rescore", str(config.RUNS / "baseline_manuals_dev.jsonl"))
    assert "Per question" in capsys.readouterr().out


def test_submit_once(monkeypatch):
    monkeypatch.setattr(config, "PARTICIPANT", "P99")
    lab("submit", "manuals")
    assert (config.SUBMISSIONS / "P99_manuals_test.jsonl").exists()
    with pytest.raises(SystemExit):
        lab("submit", "manuals")
    lab("submit", "manuals", "--force")


def test_vectorstore_filters():
    pytest.importorskip("chromadb")
    from labkit.vectorstore import ChromaStore
    chunks = copilot.CopilotBaseline().chunk(copilot.load_documents())
    store = ChromaStore(chunks)
    assert len(store.search("refund window", k=5)) == 5
    hits = store.search("refund window", k=5, where={"type": "policy"})
    assert hits and all(c.meta["type"] == "policy" for c, _ in hits)
    hits = store.search("printer", k=10, where={"type": {"$in": ["manual", "ticket"]}})
    assert hits and all(c.meta["type"] in ("manual", "ticket") for c, _ in hits)


def test_retrieval_only_does_not_replace_baseline(capsys):
    lab("copilot", "--pipeline", "baseline", "--ids", "D03", "--brief")
    lab("copilot", "--pipeline", "baseline", "--retrieval-only", "--brief")
    saved = {r["id"]: r for r in score.load(config.RUNS / "baseline_copilot_dev.jsonl")}
    assert set(saved) == {"D03"} and saved["D03"]["answer"] == "mock"
    assert "by design" in capsys.readouterr().out


def test_runs_accumulate_and_partial_baseline_is_not_compared(capsys):
    lab("copilot", "--pipeline", "baseline", "--ids", "D03", "--brief")
    lab("copilot", "--pipeline", "baseline", "--ids", "D09", "--brief")
    assert {r["id"] for r in score.load(config.RUNS / "baseline_copilot_dev.jsonl")} == {"D03", "D09"}
    lab("copilot", "--ids", "D03", "D16", "--brief")
    assert "Not compared" in capsys.readouterr().out


def test_submit_needs_own_id(monkeypatch):
    monkeypatch.setattr(config, "PARTICIPANT", "P00")
    with pytest.raises(SystemExit):
        lab("submit", "manuals")


def test_free_vision_model_choice():
    def m(i, image=True):
        return {"id": i, "architecture": {"input_modalities": ["text", "image"] if image else ["text"]}}
    live = [m("inclusionai/ling-3.2-flash:free"), m("baidu/ernie-5.5-flash-preview:free", image=False),
            m("nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"), m("google/gemma-4-26b-a4b-it:free"),
            m("google/gemma-4-31b-it:free"), m("openai/gpt-5-mini")]
    assert llm.free_vision_models(live) == ["google/gemma-4-31b-it:free", "google/gemma-4-26b-a4b-it:free",
                                            "inclusionai/ling-3.2-flash:free"]
    assert llm.free_vision_models([m("someone/new-vl:free")]) == ["someone/new-vl:free"]
