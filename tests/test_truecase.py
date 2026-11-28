from app.text import turkish_lower
from app.truecase import build_vocabulary, truecase

CORPUS = [
    "QLoRA reduces memory. 3 QLORA Finetuning. We compare QLoRA with LoRA and LoRA.",
    "ARES and ARES beat RAGAS; Ragas, Ragas and Ragas are reference-free.",
    "The table shows results. Table 2 lists them. Another table here. Self-RAG and Self-RAG.",
    "Code: https://github.com/artidoro/qlora and https://github.com/x/ares.",
    "ISSUP and ISSUP tokens. Kim and Kim wrote it.",
]
VOCAB = build_vocabulary(CORPUS, doc_names=["ragas"])


def test_names_get_their_usual_spelling():
    assert truecase("qlora ve lora'nın farkı ne? ares ile ragas", VOCAB) == (
        "QLoRA ve LoRA'nın farkı ne? ARES ile Ragas"
    )


def test_urls_do_not_count_as_lowercase_use():
    assert VOCAB["qlora"] == "QLoRA" and VOCAB["ares"] == "ARES"


def test_common_words_and_capitalized_only_names_are_left_alone():
    assert "table" not in VOCAB  # mostly lowercase in the corpus
    assert truecase("kim yazdı?", VOCAB) == "kim yazdı?"  # "Kim" is not name-like


def test_capitalized_input_is_kept_as_typed():
    assert truecase("Self-RAG ve SELF-RAG", VOCAB) == "Self-RAG ve SELF-RAG"


def test_turkish_lowercase_dotless_i_still_matches():
    assert truecase(turkish_lower("ISSUP nedir?"), VOCAB) == "ISSUP nedir?"  # "ıssup"
