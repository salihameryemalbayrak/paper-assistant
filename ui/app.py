"""Streamlit page: ask a question in Turkish, get a cited answer from the papers.

A thin client of the HTTP API (app/api.py): no model is loaded here. Streamlit reruns
this whole script on every interaction, so the last answer lives in st.session_state.

Usage (the API must be running, see README):
    uv run --group ui streamlit run ui/app.py
"""

import streamlit as st
from client import EXAMPLES, KINDS, ApiError, UiSettings, ask, health, source_title

settings = UiSettings()
st.set_page_config(page_title="Makale Asistanı", page_icon="📄", layout="centered")
st.title("Makale Asistanı")
st.caption("Türkçe soru, İngilizce makaleler: her iddia sayfa ve bölümüyle kaynak gösterilir.")

with st.sidebar:
    status = health(settings)
    if status:
        st.success(f"API hazır · {status['chunks']} chunk")
    else:
        st.error(f"API'ye ulaşılamıyor: {settings.api_url}")
    st.subheader("Örnek sorular")
    for example in EXAMPLES:
        st.button(example, on_click=lambda q=example: st.session_state.update(question=q))

question = st.text_area("Soru", key="question", height=90, max_chars=1000)
if st.button("Sor", type="primary", disabled=not question.strip()):
    with st.spinner("Soru çevriliyor, makalelerde aranıyor, cevap yazılıyor..."):
        try:
            st.session_state["result"] = ask(question, settings)
            st.session_state.pop("error", None)
        except ApiError as e:
            st.session_state["error"] = str(e)

if error := st.session_state.get("error"):
    st.error(error)
elif result := st.session_state.get("result"):
    label, color = KINDS.get(result["kind"], (result["kind"], "gray"))
    st.badge(label, color=color)
    st.markdown(result["answer"])
    if result["invented_citations"]:
        st.warning("Bağlamda olmayan kaynak etiketi: " + ", ".join(result["invented_citations"]))

    st.subheader("Kaynaklar")
    st.caption("Modele verilen metin parçaları; bağlantı PDF'i ilgili sayfada açar.")
    for source in result["sources"]:
        with st.expander(source_title(source)):
            if source["url"]:
                st.markdown(f"[PDF'i s.{source['pages'][0]} sayfasında aç]({source['url']})")
            st.text(source["text"])

    details = f"{result['seconds']} sn · {result['llm']} · {result['retriever']}"
    if result["query_en"]:
        details += f" · arama sorgusu (EN): {result['query_en']}"
    st.caption(details)
