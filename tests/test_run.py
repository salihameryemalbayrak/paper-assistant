from langchain_core.documents import Document

from eval.dataset import SourceRef
from eval.retrieval_metrics import recall_at_k
from eval.run import to_hit, unique_path


def test_hit_covers_every_page_of_the_chunk():
    doc = Document(page_content="...", metadata={"paper": "ragas", "page": 2, "pages": [2, 3]})

    hit = to_hit(doc)

    assert hit == {SourceRef(paper="ragas", page=2), SourceRef(paper="ragas", page=3)}
    # a question whose answer is on page 3 counts this chunk as relevant
    assert recall_at_k([hit], [SourceRef(paper="ragas", page=3)], k=1) == 1.0


def test_unique_path_never_overwrites(tmp_path):
    first = tmp_path / "2026-11-25_dense.json"
    assert unique_path(first) == first
    first.write_text("{}")
    assert unique_path(first).name == "2026-11-25_dense_2.json"
    (tmp_path / "2026-11-25_dense_2.json").write_text("{}")
    assert unique_path(first).name == "2026-11-25_dense_3.json"


def test_quality_gate_reports_only_failed_thresholds():
    from eval.run import quality_gate

    result = {"metrics": {"all": {"recall@5": 0.70}},
              "evidence": {"all": {"evidence_recall@5": 0.60}}}  # fmt: skip
    assert quality_gate(result, None, None) == []
    assert quality_gate(result, 0.65, 0.55) == []
    assert quality_gate(result, 0.74, 0.55) == ["recall@5 0.700 < 0.74"]


def test_percentile_nearest_rank():
    from eval.run import percentile

    values = [float(v) for v in range(1, 21)]  # 1..20
    assert percentile(values, 50) == 10.0
    assert percentile(values, 95) == 19.0
    assert percentile([7.0], 95) == 7.0
