"""Restore the usual spelling of paper, model and dataset names in a question ("truecasing").

Why: the translation LLM recognizes names by their spelling. Typed in lowercase ("ares",
"react", "qlora") it can take them for ordinary words, drop or mistranslate them, and BM25
never sees the name; the dense model is case-sensitive too. With all 41 answerable eval
questions in lowercase, evidence recall@5 fell from 0.707 to 0.493 (D47).

The vocabulary comes from the corpus, not from a hand-written list:
- name-like words of the papers: an uppercase letter after the first one, or a digit with
  an uppercase letter (QLoRA, vLLM, ARES, ReAct, ColBERTv2, GPT-4, MMLU), that the corpus
  rarely writes in all-lowercase (at most LOWERCASE_SHARE of the time: "vllm" once against
  dozens of "vLLM"; "table" nearly always, so "Table" is not a name);
- the papers' own names from data/SOURCES.md (Ragas, Mistral, Contriever), same rule.
URLs and code paths are not counted: "github.com/artidoro/qlora" is an address, not prose.
Capitalized-only words in general are left out on purpose: author names such as "Kim"
would turn the Turkish question word "kim" into a name.

Only words typed entirely in lowercase are changed: a name the user already capitalized
("Self-RAG") stays as typed. Lookup ignores case with Turkish letters folded (ı = i), so
"ıssup" (Turkish lowercase of "ISSUP") still matches. Suffixes stay: "qlora'nın" ->
"QLoRA'nın".
"""

import re
from collections import Counter, defaultdict
from collections.abc import Iterable

# a word, optionally joined by "." or "-" (same idea as the BM25 tokenizer): GPT-4, Self-RAG
_WORD = re.compile(r"[^\W_]+(?:[.\-][^\W_]+)*")
MIN_COUNT = 2  # a name must appear at least twice in the corpus
LOWERCASE_SHARE = 0.1  # ... and in all-lowercase in at most 10% of its occurrences
_PATH = re.compile(r"\S*/\S*")  # URLs and code paths: pieces containing "/"


def fold(word: str) -> str:
    """Case-insensitive key; Turkish I/İ/ı folded to i."""
    return word.replace("İ", "i").replace("I", "i").lower().replace("ı", "i")


def name_like(word: str) -> bool:
    has_digit = any(c.isdigit() for c in word)
    return any(c.isupper() for c in word[1:]) or (has_digit and any(c.isupper() for c in word))


def build_vocabulary(texts: Iterable[str], doc_names: Iterable[str] = ()) -> dict[str, str]:
    """folded form -> usual spelling, for words the corpus treats as names."""
    surfaces: dict[str, Counter[str]] = defaultdict(Counter)
    for text in texts:
        for word in _WORD.findall(_PATH.sub(" ", text)):
            surfaces[fold(word)][word] += 1

    def usual_spelling(key: str) -> str | None:
        """Most frequent capitalized spelling, if the corpus treats the word as a name."""
        counts = surfaces.get(key)
        if not counts or sum(counts.values()) < MIN_COUNT:
            return None
        lower = sum(n for w, n in counts.items() if w == w.lower())
        capitalized = Counter({w: n for w, n in counts.items() if w != w.lower()})
        if not capitalized or lower > LOWERCASE_SHARE * sum(counts.values()):
            return None
        # prefer a mixed-case spelling over the all-caps one of headings and tables:
        # "QLoRA" over "QLORA" ("3 QLORA Finetuning"), "Ragas" over "RAGAS"
        mixed = Counter({w: n for w, n in capitalized.items() if w != w.upper()})
        return (mixed or capitalized).most_common(1)[0][0]

    vocab: dict[str, str] = {}
    for key in surfaces:
        spelling = usual_spelling(key)
        if spelling and name_like(spelling):
            vocab[key] = spelling
    for name in doc_names:  # the papers' names, also when only capitalized ("Ragas")
        if spelling := usual_spelling(fold(name)):
            vocab[fold(name)] = spelling
    return vocab


def truecase(text: str, vocab: dict[str, str]) -> str:
    """Replace known names by their usual spelling; everything else stays as typed."""

    def replace(m: re.Match[str]) -> str:
        word = m.group(0)
        return vocab.get(fold(word), word) if word == word.lower() else word

    return _WORD.sub(replace, text)


def doc_names_from_sources(sources) -> list[str]:
    """Short names ("contriever") and title names before a colon ("ReAct: ...")."""
    names = []
    for s in sources:
        names.append(s.short_name.replace("_", "-"))
        if ":" in s.title:
            names.append(s.title.split(":", 1)[0].strip())
        elif len(s.title.split()) <= 3:  # "Mistral 7B", "Docling Technical Report"
            names.append(s.title.split()[0])
    return names


def load_vocabulary() -> dict[str, str]:
    """From data/chunks.jsonl and data/SOURCES.md."""
    from ingest.chunk import load_chunks
    from ingest.download import SOURCES_FILE, parse_sources

    sources = parse_sources(SOURCES_FILE.read_text(encoding="utf-8"))
    return build_vocabulary((c.text for c in load_chunks()), doc_names_from_sources(sources))
