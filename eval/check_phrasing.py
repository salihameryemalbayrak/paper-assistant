"""Check each question's wording against its source pages (the phrasing label).

A "paraphrase" question must not reuse the source's distinctive words; otherwise it is a
term question in disguise and BM25 finds it by word matching. For every answerable
question, this lists the rare words that the English question shares with its source
pages. Rare: found in fewer than RARE_DF of all chunks. The document's own name and
title words are allowed (a question has to say which document it asks about).

No LLM, no Qdrant: reads eval/dataset.jsonl, eval/translations.jsonl, data/chunks.jsonl.

Usage:
    uv run python -m eval.check_phrasing
"""

from collections import Counter
from collections.abc import Iterable

from app.bm25 import tokenize
from eval.dataset import Phrasing, QuestionType, load_dataset
from eval.translations import TRANSLATIONS, load_translations

RARE_DF = 0.02  # a word in < 2% of the chunks counts as distinctive


def rare_overlap(
    question: str,
    source_texts: Iterable[str],
    doc_freq: Counter[str],
    n_chunks: int,
    allowed: set[str],
) -> list[str]:
    """Rare words of the question that also appear in its source texts."""
    source_words = {w for text in source_texts for w in tokenize(text)}
    shared = set(tokenize(question)) & source_words - allowed
    return sorted(w for w in shared if doc_freq[w] / n_chunks < RARE_DF)


def main() -> None:
    from eval.run import DATASET
    from ingest.chunk import load_chunks
    from ingest.download import SOURCES_FILE, parse_sources

    items = load_dataset(DATASET)
    translations = load_translations(TRANSLATIONS, items)
    chunks = load_chunks()
    doc_freq: Counter[str] = Counter(w for c in chunks for w in set(tokenize(c.text)))
    titles = {
        s.short_name: set(tokenize(s.title)) | set(tokenize(s.short_name.replace("_", " ")))
        for s in parse_sources(SOURCES_FILE.read_text(encoding="utf-8"))
    }

    warnings = 0
    for item in items:
        if item.type == QuestionType.UNANSWERABLE:
            continue
        row = translations[item.id]
        english = row.en_fixed or row.en
        pages = {(s.paper, s.page) for s in item.sources}
        texts = [c.text for c in chunks if any((c.paper, p) in pages for p in c.pages)]
        allowed = set().union(*(titles[s.paper] for s in item.sources))
        shared = rare_overlap(english, texts, doc_freq, len(chunks), allowed)
        flag = ""
        if item.phrasing == Phrasing.PARAPHRASE and shared:
            flag, warnings = "  <- WARNING: paraphrase reuses source terms", warnings + 1
        print(f"{item.id} {item.phrasing.value:<10} {', '.join(shared) or '-'}{flag}")
    print(f"\nparaphrase questions reusing rare source terms: {warnings}")


if __name__ == "__main__":
    main()
