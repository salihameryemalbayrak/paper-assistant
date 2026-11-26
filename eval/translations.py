"""English translations of the eval questions, generated once and reviewed by a human.

Why a file: the fast eval must not call an LLM (speed, CI, reproducibility). Every
retrieval run reads the same stored translations, so a change in Recall comes from the
retriever, not from a different translation.

Fields:
    en        the model's raw translation; never edited (it is what the real system sees)
    en_fixed  the human correction, empty when the raw translation is fine
    reviewed  true once a human has checked the line

Usage:
    uv run python -m eval.translations           # first run: translate all questions
    uv run python -m eval.translations --missing # translate only new questions, keep the rest
    uv run python -m eval.translations --force   # regenerate all (discards the review!)
"""

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

from pydantic import BaseModel

from eval.dataset import EvalItem, load_dataset

DATASET = Path("eval/dataset.jsonl")
TRANSLATIONS = Path("eval/translations.jsonl")


class Translation(BaseModel):
    id: str
    question: str  # the Turkish question it was made from, to detect stale translations
    en: str
    en_fixed: str = ""
    reviewed: bool = False
    model: str
    date: str


def read_rows(path: Path) -> list[Translation]:
    return [
        Translation.model_validate(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_translations(path: Path, items: list[EvalItem]) -> dict[str, Translation]:
    """id -> translation; fails if a question is missing or was edited after translating."""
    rows = read_rows(path)
    by_id = {row.id: row for row in rows}
    for item in items:
        row = by_id.get(item.id)
        if row is None:
            raise ValueError(f"{path}: no translation for {item.id}")
        if row.question != item.question:
            raise ValueError(f"{path}: {item.id} question changed since translation; regenerate")
    return by_id


def main() -> None:
    from app.config import get_settings
    from app.llm import get_chat_model
    from app.translate import build_translator

    parser = argparse.ArgumentParser(description="Translate the eval questions into English.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--force", action="store_true", help="overwrite (discards the review)")
    mode.add_argument("--missing", action="store_true", help="add only untranslated questions")
    args = parser.parse_args()
    if TRANSLATIONS.exists() and not (args.force or args.missing):
        sys.exit(
            f"{TRANSLATIONS} exists; it may hold a human review. "
            "Use --missing to add new questions or --force to overwrite."
        )

    settings = get_settings()
    translator = build_translator(get_chat_model(settings))
    items = load_dataset(DATASET)
    kept: list[Translation] = []
    if args.missing and TRANSLATIONS.exists():
        kept = read_rows(TRANSLATIONS)
        current = {i.id: i.question for i in items}
        stale = [r.id for r in kept if r.id in current and r.question != current[r.id]]
        if stale:
            sys.exit(f"edited since translation: {stale}; fix by hand or use --force")
    done = {r.id for r in kept}
    rows, seconds, unchanged = [], [], 0
    for item in (i for i in items if i.id not in done):
        start = time.perf_counter()
        en = translator.invoke(item.question)
        seconds.append(time.perf_counter() - start)
        unchanged += en == item.question  # fallback or no translation: worth a look
        rows.append(
            Translation(
                id=item.id,
                question=item.question,
                en=en,
                model=settings.llm_model,
                date=date.today().isoformat(),
            )
        )
        print(f"{item.id}: {en}")

    if not rows:
        print("nothing to translate")
        return
    TRANSLATIONS.write_text(
        "".join(json.dumps(r.model_dump(), ensure_ascii=False) + "\n" for r in kept + rows),
        encoding="utf-8",
    )
    seconds.sort()
    print(
        f"\n{len(rows)} new questions (+{len(kept)} kept) -> {TRANSLATIONS} [{settings.llm_model}]"
    )
    print("new lines have reviewed=false: check them by hand")
    print(f"returned unchanged: {unchanged}")
    print(f"seconds: median {seconds[len(seconds) // 2]:.2f}, max {seconds[-1]:.2f}")


if __name__ == "__main__":
    main()
