from app.text import normalize_text, turkish_lower


def test_ligatures_are_expanded():
    assert normalize_text("ﬁne-tuning and ﬂow") == "fine-tuning and flow"


def test_invisible_characters_are_removed():
    # soft hyphen inside a word, zero-width space, BOM
    assert normalize_text("﻿re­trieval​") == "retrieval"


def test_decomposed_turkish_letters_become_precomposed():
    decomposed = "şekil"  # "s" + combining cedilla
    assert decomposed != "şekil"
    assert normalize_text(decomposed) == "şekil"


def test_spaces_collapse_but_newlines_stay():
    assert normalize_text("  Tablo  3\t\tsonuçlar\nŞekil 2  ") == "Tablo 3 sonuçlar\nŞekil 2"


def test_python_default_lower_is_wrong_for_turkish():
    # Documents the pitfall that turkish_lower() exists to fix.
    assert "I".lower() == "i"
    assert "İ".lower() == "i̇"  # two characters: i + combining dot


def test_turkish_lower():
    assert turkish_lower("IĞDIR İSTANBUL") == "ığdır istanbul"
    assert turkish_lower("ŞEKİL ÇİZELGE ÖZET ÜÇ") == "şekil çizelge özet üç"
