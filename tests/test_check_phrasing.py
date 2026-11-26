from collections import Counter

from eval.check_phrasing import rare_overlap

# 100 chunks: "retrieval" is everywhere, "ccpairs" in one chunk only
DOC_FREQ = Counter({"retrieval": 60, "ccpairs": 1, "pairs": 5, "e5": 1, "text": 40})


def overlap(question: str, allowed: frozenset[str] = frozenset()) -> list[str]:
    source = ["E5 is trained on CCPairs, text pairs used for retrieval."]
    return rare_overlap(question, source, DOC_FREQ, 100, set(allowed))


def test_rare_shared_words_are_reported():
    assert overlap("How many CCPairs pairs remain?") == ["ccpairs"]


def test_common_words_and_the_document_name_are_ignored():
    assert overlap("What retrieval text does E5 use?", frozenset({"e5"})) == []


def test_paraphrase_without_source_terms_is_clean():
    assert overlap("How much web data was kept after cleaning?") == []
