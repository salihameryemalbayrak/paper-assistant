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
| ares | 2311.09476v2 | ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems | CC BY 4.0 |
| colbertv2 | 2112.01488v3 | ColBERTv2: Effective and Efficient Retrieval via Lightweight Late Interaction | CC BY 4.0 |
| contriever | 2112.09118v4 | Unsupervised Dense Information Retrieval with Contrastive Learning | CC BY 4.0 |
| me5 | 2402.05672v1 | Multilingual E5 Text Embeddings: A Technical Report | CC BY 4.0 |
| raptor | 2401.18059v1 | RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval | CC BY 4.0 |
| graphrag | 2404.16130v2 | From Local to Global: A Graph RAG Approach to Query-Focused Summarization | CC BY 4.0 |
| cot | 2201.11903v6 | Chain-of-Thought Prompting Elicits Reasoning in Large Language Models | CC BY 4.0 |
| self_consistency | 2203.11171v4 | Self-Consistency Improves Chain of Thought Reasoning in Language Models | CC BY 4.0 |
| react | 2210.03629v3 | ReAct: Synergizing Reasoning and Acting in Language Models | CC BY 4.0 |
| reflexion | 2303.11366v4 | Reflexion: Language Agents with Verbal Reinforcement Learning | CC BY 4.0 |
| mistral | 2310.06825v1 | Mistral 7B | CC BY 4.0 |
| vllm | 2309.06180v1 | Efficient Memory Management for Large Language Model Serving with PagedAttention | CC BY 4.0 |
| docling | 2408.09869v5 | Docling Technical Report | CC BY 4.0 |

Links: `https://arxiv.org/abs/<arxiv_id>` (e.g. https://arxiv.org/abs/2309.15217v2).
