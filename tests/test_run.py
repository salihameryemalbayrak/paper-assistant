from langchain_core.documents import Document

from eval.dataset import SourceRef
from eval.retrieval_metrics import recall_at_k
from eval.run import to_hit


def test_hit_covers_every_page_of_the_chunk():
    doc = Document(page_content="...", metadata={"paper": "ragas", "page": 2, "pages": [2, 3]})

    hit = to_hit(doc)

    assert hit == {SourceRef(paper="ragas", page=2), SourceRef(paper="ragas", page=3)}
    # a question whose answer is on page 3 counts this chunk as relevant
    assert recall_at_k([hit], [SourceRef(paper="ragas", page=3)], k=1) == 1.0
