from ingest.elements import Element, ElementType, load_elements, save_elements


def test_elements_round_trip_with_turkish_text(tmp_path):
    elements = [
        Element(paper="p", page=1, section="", type=ElementType.HEADING, text="Giriş"),
        Element(paper="p", page=2, section="Giriş", type=ElementType.TEXT, text="Şekil ığdır"),
        Element(paper="p", page=2, section="Giriş", type=ElementType.TABLE, text="| a |\n|---|"),
    ]
    path = tmp_path / "p.jsonl"

    save_elements(elements, path)

    assert load_elements(path) == elements
