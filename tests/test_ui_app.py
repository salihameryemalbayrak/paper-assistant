"""Streamlit page rendered without a browser (AppTest). Needs the "ui" group; CI skips it."""

import pytest

pytest.importorskip("streamlit")

from pathlib import Path  # noqa: E402

from streamlit.testing.v1 import AppTest  # noqa: E402

# from_file resolves relative paths against the calling file, not the working directory
PAGE = str(Path(__file__).parent.parent / "ui" / "app.py")


def test_page_renders_and_reports_an_unreachable_api(monkeypatch):
    monkeypatch.setenv("API_URL", "http://127.0.0.1:9")  # nothing listens there
    page = AppTest.from_file(PAGE, default_timeout=30).run()
    assert not page.exception
    assert page.title[0].value == "Makale Asistanı"
    assert "API'ye ulaşılamıyor" in page.sidebar.error[0].value
    ask = next(b for b in page.button if b.label == "Sor")
    assert ask.disabled  # empty question


def test_example_button_fills_the_question(monkeypatch):
    monkeypatch.setenv("API_URL", "http://127.0.0.1:9")
    page = AppTest.from_file(PAGE, default_timeout=30).run()
    page.sidebar.button[0].click().run()
    assert page.text_area(key="question").value.startswith("QLoRA")
