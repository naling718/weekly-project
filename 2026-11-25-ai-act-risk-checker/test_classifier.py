import json
from pathlib import Path

import pytest

from app import app
from classifier import classify

SAMPLES = json.loads((Path(__file__).parent / "samples.json").read_text())


@pytest.mark.parametrize("s", SAMPLES, ids=[s["name"] for s in SAMPLES])
def test_samples_get_expected_tier(s):
    assert classify(s["description"])["tier"] == s["expected"]


def test_highest_tier_wins_and_all_reasons_listed():
    r = classify("A chatbot that screens job candidates by reading their emotions in interviews.")
    assert r["tier"] == "high"
    refs = [m["ref"] for m in r["matches"]]
    assert "Annex III(4)" in refs and "Art. 50(1)" in refs
    assert refs.index("Annex III(4)") < refs.index("Art. 50(1)")


def test_fraud_detection_is_carved_out_of_credit_rule():
    assert classify("Credit scoring for loan decisions")["tier"] == "high"
    assert classify("Credit card fraud scoring")["tier"] == "minimal"


def test_common_words_do_not_trigger_rules():
    r = classify("Summarises long sentences, for example in database migration logs.")
    assert r == {"tier": "minimal", "matches": [], "obligations": r["obligations"]}


@pytest.mark.parametrize("bad", ["", "   ", None, 42, "x" * 5001])
def test_rejects_invalid_input(bad):
    with pytest.raises(ValueError):
        classify(bad)


def test_api_and_page():
    c = app.test_client()
    r = c.post("/api/classify", json={"description": "Assigns citizens a social score"})
    assert r.status_code == 200 and r.get_json()["tier"] == "unacceptable"
    assert c.post("/api/classify", json={}).status_code == 400
    page = c.post("/", data={"description": "<script>alert(1)</script> chatbot"}).get_data(as_text=True)
    assert "LIMITED" in page and "<script>alert" not in page
