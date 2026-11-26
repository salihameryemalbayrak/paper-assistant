import json
from pathlib import Path

import pytest

from eval.dataset import EvalItem, SourceRef, load_dataset
from eval.translations import load_translations

ITEM = EvalItem(
    verified=True,  # human-verified: no evidence needed
    phrasing="term",
    id="q1",
    type="single_page",
    question="Seyrek arama neden zayıf?",
    answer="...",
    sources=[SourceRef(paper="bge_m3", page=2)],
)


def write(tmp_path: Path, **overrides) -> Path:
    row = {"id": "q1", "question": ITEM.question, "en": "Why is sparse search weak?",
           "model": "test-model", "date": "2026-11-25", **overrides}  # fmt: skip
    path = tmp_path / "translations.jsonl"
    path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def test_loads_with_review_defaults(tmp_path):
    row = load_translations(write(tmp_path), [ITEM])["q1"]
    assert row.en == "Why is sparse search weak?"
    assert row.en_fixed == "" and row.reviewed is False


def test_missing_translation_fails(tmp_path):
    other = ITEM.model_copy(update={"id": "q2"})
    with pytest.raises(ValueError, match="no translation for q2"):
        load_translations(write(tmp_path), [ITEM, other])


def test_edited_question_makes_translation_stale(tmp_path):
    edited = ITEM.model_copy(update={"question": "Seyrek arama neden güçlü?"})
    with pytest.raises(ValueError, match="question changed"):
        load_translations(write(tmp_path), [edited])


def test_repository_file_matches_the_eval_set():
    items = load_dataset(Path("eval/dataset.jsonl"))
    assert set(load_translations(Path("eval/translations.jsonl"), items)) >= {i.id for i in items}
