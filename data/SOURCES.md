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

## Attribution

Required by CC BY 4.0 (Section 3(a)) wherever this project shares material from these
papers, including the chunk file published as a GitHub Release asset for CI.

- **ragas**: Ragas: Automated Evaluation of Retrieval Augmented Generation. Shahul Es, Jithin James, Luis Espinosa-Anke, Steven Schockaert.
  arXiv: https://arxiv.org/abs/2309.15217v2 · License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
- **self_rag**: Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection. Akari Asai, Zeqiu Wu, Yizhong Wang, Avirup Sil, Hannaneh Hajishirzi.
  arXiv: https://arxiv.org/abs/2310.11511v1 · License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
- **bge_m3**: M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation. Jianlv Chen, Shitao Xiao, Peitian Zhang, Kun Luo, Defu Lian, Zheng Liu.
  arXiv: https://arxiv.org/abs/2402.03216v5 · License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
- **e5**: Text Embeddings by Weakly-Supervised Contrastive Pre-training. Liang Wang, Nan Yang, Xiaolong Huang, Binxing Jiao, Linjun Yang, Daxin Jiang, Rangan Majumder, Furu Wei.
  arXiv: https://arxiv.org/abs/2212.03533v2 · License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
- **qlora**: QLoRA: Efficient Finetuning of Quantized LLMs. Tim Dettmers, Artidoro Pagnoni, Ari Holtzman, Luke Zettlemoyer.
  arXiv: https://arxiv.org/abs/2305.14314v1 · License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
- **ares**: ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems. Jon Saad-Falcon, Omar Khattab, Christopher Potts, Matei Zaharia.
  arXiv: https://arxiv.org/abs/2311.09476v2 · License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
- **colbertv2**: ColBERTv2: Effective and Efficient Retrieval via Lightweight Late Interaction. Keshav Santhanam, Omar Khattab, Jon Saad-Falcon, Christopher Potts, Matei Zaharia.
  arXiv: https://arxiv.org/abs/2112.01488v3 · License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
- **contriever**: Unsupervised Dense Information Retrieval with Contrastive Learning. Gautier Izacard, Mathilde Caron, Lucas Hosseini, Sebastian Riedel, Piotr Bojanowski, Armand Joulin, Edouard Grave.
  arXiv: https://arxiv.org/abs/2112.09118v4 · License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
- **me5**: Multilingual E5 Text Embeddings: A Technical Report. Liang Wang, Nan Yang, Xiaolong Huang, Linjun Yang, Rangan Majumder, Furu Wei.
  arXiv: https://arxiv.org/abs/2402.05672v1 · License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
- **raptor**: RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval. Parth Sarthi, Salman Abdullah, Aditi Tuli, Shubh Khanna, Anna Goldie, Christopher D. Manning.
  arXiv: https://arxiv.org/abs/2401.18059v1 · License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
- **graphrag**: From Local to Global: A Graph RAG Approach to Query-Focused Summarization. Darren Edge, Ha Trinh, Newman Cheng, Joshua Bradley, Alex Chao, Apurva Mody, Steven Truitt, Dasha Metropolitansky, Robert Osazuwa Ness, Jonathan Larson.
  arXiv: https://arxiv.org/abs/2404.16130v2 · License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
- **cot**: Chain-of-Thought Prompting Elicits Reasoning in Large Language Models. Jason Wei, Xuezhi Wang, Dale Schuurmans, Maarten Bosma, Brian Ichter, Fei Xia, Ed Chi, Quoc Le, Denny Zhou.
  arXiv: https://arxiv.org/abs/2201.11903v6 · License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
- **self_consistency**: Self-Consistency Improves Chain of Thought Reasoning in Language Models. Xuezhi Wang, Jason Wei, Dale Schuurmans, Quoc Le, Ed Chi, Sharan Narang, Aakanksha Chowdhery, Denny Zhou.
  arXiv: https://arxiv.org/abs/2203.11171v4 · License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
- **react**: ReAct: Synergizing Reasoning and Acting in Language Models. Shunyu Yao, Jeffrey Zhao, Dian Yu, Nan Du, Izhak Shafran, Karthik Narasimhan, Yuan Cao.
  arXiv: https://arxiv.org/abs/2210.03629v3 · License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
- **reflexion**: Reflexion: Language Agents with Verbal Reinforcement Learning. Noah Shinn, Federico Cassano, Edward Berman, Ashwin Gopinath, Karthik Narasimhan, Shunyu Yao.
  arXiv: https://arxiv.org/abs/2303.11366v4 · License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
- **mistral**: Mistral 7B. Albert Q. Jiang, Alexandre Sablayrolles, Arthur Mensch, Chris Bamford, Devendra Singh Chaplot, Diego de las Casas, Florian Bressand, Gianna Lengyel, Guillaume Lample, Lucile Saulnier, Lélio Renard Lavaud, Marie-Anne Lachaux, Pierre Stock, Teven Le Scao, Thibaut Lavril, Thomas Wang, Timothée Lacroix, William El Sayed.
  arXiv: https://arxiv.org/abs/2310.06825v1 · License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
- **vllm**: Efficient Memory Management for Large Language Model Serving with PagedAttention. Woosuk Kwon, Zhuohan Li, Siyuan Zhuang, Ying Sheng, Lianmin Zheng, Cody Hao Yu, Joseph E. Gonzalez, Hao Zhang, Ion Stoica.
  arXiv: https://arxiv.org/abs/2309.06180v1 · License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
  Copyright: The PDF carries the notice "© 2023 Copyright held by the owner/author(s)." (ACM, SOSP '23); retained in the extracted text.
- **docling**: Docling Technical Report. Christoph Auer, Maksym Lysak, Ahmed Nassar, Michele Dolfi, Nikolaos Livathinos, Panos Vagenas, Cesar Berrospi Ramis, Matteo Omenetti, Fabian Lindlbauer, Kasper Dinkla, Lokesh Mishra, Yusik Kim, Shubham Gupta, Rafael Teixeira de Lima, Valery Weber, Lucas Morin, Ingmar Meijer, Viktor Kuropiatnyk, Peter W. J. Staar.
  arXiv: https://arxiv.org/abs/2408.09869v5 · License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
  Copyright: Pages 7–9 show the first page of another paper (DocLayNet, with its ACM notice) as a figure; that text is part of the figure.

### Modifications

Material shared by this project (the chunk file) is modified from the original PDFs:
- text, tables and figure captions extracted with Docling; tables converted to Markdown;
- Unicode normalized; page headers/footers and the reference lists removed;
- split into chunks of at most ~400 tokens, each prefixed with "paper title > section".
The papers are provided "as is" by their authors, without warranties (CC BY 4.0, Section 5).
