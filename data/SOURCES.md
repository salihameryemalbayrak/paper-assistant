# Sources

Papers used in this project. Only openly licensed papers (CC BY / CC0) are allowed.
PDFs are **not** stored in the repository; `uv run python -m ingest.download` fetches them
into `data/raw/` and re-checks each license against arXiv before downloading.

Versions are pinned (e.g. `v2`) because page numbers in the eval set depend on the exact PDF.

| short_name | arxiv_id | title | license |
|---|---|---|---|
| ragas | 2309.15217v2 | Ragas: Automated Evaluation of Retrieval Augmented Generation | CC BY 4.0 |
| self_rag | 2310.11511v1 | Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection | CC BY 4.0 |
| bge_m3 | 2402.03216v5 | M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation | CC BY 4.0 |
| e5 | 2212.03533v2 | Text Embeddings by Weakly-Supervised Contrastive Pre-training | CC BY 4.0 |
| qlora | 2305.14314v1 | QLoRA: Efficient Finetuning of Quantized LLMs | CC BY 4.0 |

Links: `https://arxiv.org/abs/<arxiv_id>` (e.g. https://arxiv.org/abs/2309.15217v2).
