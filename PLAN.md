# PLAN — Çok Modlu Makale Asistanı (agentic RAG)

Bu dosya projenin aşama aşama yol haritası. Kurallar ve teknoloji seçimleri için: `CLAUDE.md`.
Takvim yok; her aşama, "bitti" kriteri sağlanınca tamamlanmış sayılır.

**Her aşamada şu başlıklar var:**
- **Hedef:** Bu aşama neden var?
- **Yapılacaklar:** Somut işler.
- **Çıktı / komut:** Aşama sonunda çalıştırılabilen şey. Komutlar plan aşamasında taslaktır; kesin hali README ve CLAUDE.md'deki komut tablosuna yazılır.
- **Bitti kriteri:** Ölçülebilir koşul.
- **DECISIONS.md:** Bu aşamada `docs/DECISIONS.md`'ye yazılacak "neden bu seçim" notları.
- **Yoklama:** Aşama sonunda sorulacak 2–3 soru.

---

## Genel akış (hedef mimari)

```
             ┌───────────── ingest (bir kez) ─────────────┐
PDF'ler ──► ayrıştır + OCR ──► chunk (sayfa/bölüm/tür metadata) ──► Qdrant + BM25 indeksi

             ┌───────────── sorgu (her soru) ─────────────┐
Türkçe soru ──► TR→EN çeviri ──► BM25(EN) + Dense(TR, EN) ──► RRF ──► reranker
            ──► top-k chunk ──► LLM (kaynaklı prompt) ──► Türkçe cevap + [kaynak, s., §]
                                         │
                                 Langfuse izi + eval
```

---

## Aşama 0 — İskelet

**Hedef:** Her şeyin üstüne kurulacağı temel. Model sunucusu kuralı (`LLM_BASE_URL`) ilk günden çalışsın.

**Yapılacaklar:**
- Repo klasör yapısı (`app/`, `ingest/`, `eval/`, `ui/`, `infra/`, `docs/`, `data/`, `tests/`, `notebooks/`).
- `pyproject.toml`: `uv` ile bağımlılıklar, `ruff` ve `pytest` ayarları.
- `.gitignore` (PDF'ler, indeks verisi, `.env`, model dosyaları), `.env.example`.
- `app/config.py`: `pydantic-settings` ile tüm ayarlar tek yerde (`LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`, …).
- `app/llm.py`: LangChain `ChatOpenAI` ile ayarlardan beslenen LLM istemcisi.
- Ollama kurulumu, küçük bir model (3–4B) ile "merhaba" çağrısı.
- Türkçe karakter/Unicode normalizasyonu için ilk yardımcı fonksiyon + testi.
- GitHub Actions: `ruff check` + `pytest`.
- İngilizce README iskeleti (amaç, mimari taslağı, kurulum).
- `docs/DECISIONS.md` dosyasını oluştur.

**Çıktı / komut:** `uv sync`, `uv run pytest`, `uv run python -m app.llm "Merhaba"`

**Bitti kriteri:**
- Testler ve lint yerelde ve CI'da yeşil.
- Model yalnızca `.env` değiştirilerek değiştirilebiliyor.

**DECISIONS.md:**
- LangChain nedir, neden LangChain (neden LlamaIndex değil)?
- Neden OpenAI uyumlu API soyutlaması?
- Neden `uv`?

**Yoklama:**
- `LLM_BASE_URL`'i değiştirince hangi dosyalar etkilenir?
- `ChatOpenAI` sınıfı neden Ollama ile de çalışıyor?

---

## Aşama 1 — Veri

**Hedef:** Az ama lisansı temiz veriyle başlamak.

**Yapılacaklar:**
- CC-BY / CC0 lisanslı 5 makale seç (farklı yapılarda olsun: tablo ağırlıklı, şekil ağırlıklı, en az bir taranmış sayfalı PDF).
- Her birini `data/SOURCES.md`'ye kaydet (başlık, URL, lisans, kısa ad).
- `ingest/download.py`: `SOURCES.md`'den okuyup PDF'leri `data/raw/` altına indirir (git dışında).

**Çıktı / komut:** `uv run python -m ingest.download`

**Bitti kriteri:**
- 5 PDF indirildi.
- Lisanslar kayıtlı.
- `git status` PDF göstermiyor.

**DECISIONS.md:** Neden açık lisans? "Açık erişim" ile "açık lisans" arasındaki fark.

**Yoklama:** arXiv'deki her makaleyi neden kullanamayız?

---

## Aşama 2 — Eval seti (eval-first)

**Hedef:** Sistemi kurmadan önce "iyi"nin ne demek olduğunu tanımlamak.

**Yapılacaklar:**
- 20 soruluk ilk set, `eval/dataset.jsonl` dosyasında. Her satırda:
  - soru (TR)
  - beklenen cevap
  - kaynak makale, sayfa ve bölüm
  - soru türü
- Soru türleri: tek sayfa, tablo, şekil, iki makale karşılaştırma, "dokümanda yok".
- `eval/retrieval_metrics.py`: Recall@k ve MRR (kendi yazdığın betik; kütüphane yok).
- Sahte bir retrieval çıktısıyla metrik betiğinin testleri.

**Çıktı / komut:** `uv run python -m eval.retrieval_metrics --help`, `uv run pytest tests/test_metrics.py`

**Bitti kriteri:**
- 20 soru elle doğrulandı.
- Metrik betiği testli ve doğru hesaplıyor.

**DECISIONS.md:**
- Recall@k ve MRR nedir, ne farkı var?
- Neden eval-first?

**Yoklama:**
- Recall@5 = 0.8, MRR = 0.4 ne anlama gelir?
- "Dokümanda yok" soruları retrieval metriğinde nasıl değerlendirilir?

---

## Aşama 3 — Ingest (PDF → chunk)

**Hedef:** Kaynak gösterebilmenin temeli. Her chunk sayfa ve bölüm bilgisini taşımalı.

**Yapılacaklar:**
- **Ayrıştırıcı karşılaştırması:** Docling ve PyMuPDF'i 3–5 makalede dene. Kıyas noktaları: bölüm başlığı doğruluğu, tablo kalitesi, OCR, süre, disk kullanımı. Birini seç.
- Taranmış sayfalarda OCR.
- Tablo → Markdown chunk.
- Şekil → caption chunk (opsiyonel küçük VLM açıklaması sonraya bırakılabilir).
- **Chunking:** Bölüm sınırlarına saygılı, token sınırlı. LangChain text splitter kullanılır, chunk boyutu ve örtüşme ayarlanır.
- Her chunk bir LangChain `Document` olur. Metadata: `paper`, `page`, `section`, `type` (text/table/figure), `chunk_id`.
- Türkçe/Unicode testleri.

**Çıktı / komut:** `uv run python -m ingest.build --input data/raw --out data/chunks.jsonl`

**Bitti kriteri:**
- Tüm makaleler chunk'landı.
- Rastgele 10 chunk elle kontrol edildi: sayfa ve bölüm doğru.
- Tablo ve şekil chunk'ları mevcut.

**DECISIONS.md:**
- Docling mi PyMuPDF mi (ölçümlerle)?
- Chunk boyutu ve örtüşme neden bu değerler?
- Neden bölüm farkında chunking?

**Yoklama:**
- Chunk çok büyük olursa ne olur? Çok küçük olursa?
- Örtüşme (overlap) neden var?

---

## Aşama 4 — Dense arama + uçtan uca basit RAG

**Hedef:** İlk çalışan sürüm ve **baseline** ölçümü.

**Yapılacaklar:**
- Qdrant'ı Docker ile çalıştır.
- LangChain Qdrant entegrasyonu ile indeksleme.
- **Embedding karşılaştırması:** bge-m3 ile multilingual-e5-small (Hugging Face `sentence-transformers`). Hızlı eval ile ölçülür.
- Kaynaklı cevap prompt şablonu:
  - Yalnızca verilen chunk'lardan cevap ver.
  - `[kısa_ad, s.X, §Y]` formatında kaynak göster.
  - Kaynakta yoksa "Dokümanda bulamadım." de.
- LangChain zinciri: retriever → prompt → LLM → çıktı.
- CLI: `uv run python -m app.ask "soru"`.

**Çıktı / komut:** `uv run python -m ingest.index`, `uv run python -m app.ask "..."`, `uv run python -m eval.run --fast`

**Bitti kriteri:**
- 20 soruya cevap üretiliyor.
- Baseline Recall@k/MRR `docs/benchmarks/` altına kaydedildi (model, donanım ve tarih bilgisiyle).

**DECISIONS.md:**
- Retriever nedir, zincir (chain) nedir?
- Embedding modeli seçimi (ölçümle).
- Prompt tasarımı.

**Yoklama:**
- Dense arama neden "eşanlamlı" kelimeleri bulabiliyor?
- Prompt'ta "kaynakta yoksa bulamadım de" kuralı neden önemli?

---

## Aşama 5 — Hibrit arama + sorgu çevirisi

**Hedef:** Projenin yıldızı. Her eklemenin katkısını ölçmek.

**Yapılacaklar:**
- BM25 retriever (İngilizce metin üzerinde).
- TR→EN sorgu çevirisi (LLM adımı).
- Dense arama TR ve EN sorgularla.
- Sonuçları RRF ile birleştir. LangChain'in hazır birleştirici retriever'ı kullanılır; RRF formülü (`Σ 1/(k + sıra)`) açıklanır ve elle küçük bir örnekle doğrulanır.
- **Ablation:** Her varyant hızlı eval ile ölçülür ve tabloya yazılır:
  - yalnızca dense (TR)
  - dense (TR+EN)
  - BM25 (EN)
  - hibrit, çevirisiz
  - hibrit, çevirili
- Çeviri adımının gecikmesi ölçülür.

**Çıktı / komut:** `uv run python -m eval.run --fast --variant hybrid_translate`

**Bitti kriteri:** Ablation tablosu `docs/benchmarks/` altında. Seçilen varyantın gerekçesi sayılarla yazıldı.

**DECISIONS.md:**
- Neden hibrit arama?
- RRF nasıl çalışır, neden skor normalizasyonu gerekmez?
- Sorgu çevirisi: katkısı ve bedeli.

**Yoklama:**
- BM25 hangi tür sorularda dense aramadan iyidir?
- RRF'deki `k` sabiti büyürse ne olur?

---

## Aşama 6 — Reranker

**Hedef:** İlk aşamada geniş getirilen sonuçları hassas şekilde yeniden sıralamak.

**Yapılacaklar:**
- Cross-encoder reranker (bge-reranker), LangChain'in reranker/compressor sarmalayıcısıyla.
- Akış: aday sayısı (ör. 20–50) → reranker → LLM'e giden top-k (ör. 3–8).
- Hızlı eval ve gecikme ölçümü.

**Çıktı / komut:** `uv run python -m eval.run --fast --variant hybrid_translate_rerank`

**Bitti kriteri:** Reranker'lı ve reranker'sız karşılaştırma tabloda (doğruluk + gecikme).

**DECISIONS.md:**
- Bi-encoder (embedding) ile cross-encoder (reranker) arasındaki fark.
- Neden iki aşamalı arama?

**Yoklama:**
- Reranker neden doğrudan tüm koleksiyonda kullanılmıyor?
- Aday sayısını artırmak neyi iyileştirir, neyi kötüleştirir?

---

## Aşama 7 — Tam eval + Langfuse

**Hedef:** Cevap kalitesini ölçmek ve her isteği izlenebilir yapmak.

**Yapılacaklar:**
- Eval setini 40–60 soruya genişlet (CLAUDE.md'deki tür dağılımı).
- RAGAS: faithfulness ve answer relevancy. Hakem LLM sabitlenir ve adı kaydedilir.
- "Dokümanda yok" sorularında doğru reddetme oranı (kendi metriğin).
- Kaynak formatı doğrulaması: cevaptaki her kaynak getirilen chunk'larda var mı?
- Langfuse: LangChain callback ile iz kaydı. `obs` profili ya da Langfuse Cloud. `LANGFUSE_*` yoksa iz kaydı kapalı.
- CI'a hızlı eval eklenir; eşik altına düşerse CI kırmızı olur.

**Çıktı / komut:** `uv run python -m eval.run --full`

**Bitti kriteri:**
- Tam eval raporu `docs/benchmarks/` altında.
- Bir sorgunun Langfuse izi görülebiliyor.
- CI'da hızlı eval çalışıyor.

**DECISIONS.md:**
- Faithfulness ve relevancy nedir?
- LLM-as-judge yaklaşımının sınırları.
- Neden Langfuse?

**Yoklama:**
- Faithfulness yüksek ama relevancy düşükse ne olmuştur?
- Hakem model değişirse eski sonuçlarla neden karşılaştıramayız?

---

## Aşama 8 — API + arayüz + Docker Compose

**Hedef:** Tek komutla ayağa kalkan, gösterilebilir bir sistem.

**Yapılacaklar:**
- FastAPI: `/ask` (cevap + kaynaklar) ve `/health` uç noktaları.
- Streamlit arayüz: soru kutusu, cevap, tıklanabilir kaynak listesi (makale, sayfa, bölüm).
- `infra/docker-compose.yml` profilleri: `dev` (Ollama), `gpu` (vLLM), `obs` (Langfuse).
- arm64 + amd64 imajları; Docker disk sınırı notu.
- README:
  - mimari diyagram
  - sonuç tabloları
  - ekran görüntüsü / GIF
  - kurulum adımları

**Çıktı / komut:** `docker compose -f infra/docker-compose.yml --profile dev up`

**Bitti kriteri:**
- Temiz bir makinede README adımlarıyla sistem çalışıyor.
- Arayüzden soru sorulup kaynaklı cevap alınıyor.

**DECISIONS.md:**
- Neden Streamlit?
- Compose profilleri neden var?

**Yoklama:**
- Mac'ten GPU makinesine geçerken neyi değiştiriyoruz, neyi değiştirmiyoruz?

---

## Aşama 9 — Model karşılaştırma matrisi

**Hedef:** "Küçük model + iyi arama yeterli mi?" sorusunu sayılarla cevaplamak.

**Yapılacaklar:**
- Aynı hat (aynı retrieval, aynı prompt) üç modelle çalıştırılır:
  - küçük yerel model (3–4B)
  - daha büyük açık model
  - ticari API
- Ölçülenler: doğruluk (RAGAS + reddetme oranı), gecikme (p50/p95), maliyet.
- vLLM benchmark'ı Colab notebook'unda (`notebooks/`). Sonuçlar JSON/CSV olarak kaydedilir.
- Her sonuçla birlikte donanım ve model adı yazılır.

**Çıktı / komut:** `uv run python -m eval.compare --models config/models.yaml`

**Bitti kriteri:** Karşılaştırma tablosu `docs/benchmarks/` ve README'de.

**DECISIONS.md:** Sonuçların yorumu; hangi durumda hangi model?

**Yoklama:** Küçük model hangi soru türünde en çok geride kaldı, neden?

---

## Genişletilmiş sürüm (sırayla, opsiyonel)

### G1 — LangGraph agentic akış
- Akış: planla → ara → "sonuç yeterli mi?" → (hayır: sorguyu yeniden yaz, tekrar ara; en fazla N deneme) / tablo oku / iki makaleyi karşılaştır → cevap.
- Düğümler, temel sürümdeki retrieval fonksiyonlarını kullanır.
- Eval: temel RAG ile agentic akış karşılaştırılır (özellikle karşılaştırma ve tablo sorularında). Ek gecikme de ölçülür.
- **DECISIONS.md:** LangGraph nedir? Düğüm, kenar ve durum (state) kavramları. Basit zincir neden yetmedi?

### G2 — Guardrails
- Kaynaksız cevabı engelleme.
- Prompt injection test seti (ör. PDF içine gömülü talimatlar).
- Çıktı formatı doğrulama.
- Testler CI'da çalışır.

### G3 — MCP sunucusu
- Arama aracını MCP üzerinden dışa açan küçük bir sunucu.
- Bir MCP istemcisinden test edilir.

### G4 — LoRA fine-tuning
- Hugging Face PEFT ile Colab'da küçük modele LoRA.
- Eval ile önce/sonra karşılaştırması.
- Sonuçlar `docs/benchmarks/` altında.

---

## İlerleme kontrol listesi

- [x] Aşama 0 — İskelet
- [x] Aşama 1 — Veri
- [x] Aşama 2 — Eval seti
- [ ] Aşama 3 — Ingest
- [ ] Aşama 4 — Dense + basit RAG (baseline)
- [ ] Aşama 5 — Hibrit arama + sorgu çevirisi
- [ ] Aşama 6 — Reranker
- [ ] Aşama 7 — Tam eval + Langfuse
- [ ] Aşama 8 — API + arayüz + Docker Compose
- [ ] Aşama 9 — Model karşılaştırma matrisi
- [ ] G1 — LangGraph agentic akış
- [ ] G2 — Guardrails
- [ ] G3 — MCP sunucusu
- [ ] G4 — LoRA

## Açık sorular

- Küçük yerel model hangisi olacak (Türkçe kalitesi göz önüne alınarak)? Başlangıç: `qwen3:4b`. Alternatifler `gemma3:4b`, `llama3.2:3b`; karar eval ile verilecek.
- `qwen3:4b` kısa bir cevap için yaklaşık 22 sn sürdü (M4 Air, Ollama). Muhtemel sebep: modelin cevaptan önce görünmez "düşünme" metni üretmesi. Düşünme modunu kapatma yolu dokümantasyondan kontrol edilip gecikme ve doğruluk etkisi ölçülecek.
- RAGAS hakem modeli: varsayılan olarak ücretsiz bir seçenek (daha büyük bir açık model, Colab'da). Ticari model yalnızca isteğe bağlı (bkz. CLAUDE.md, Maliyet kuralı).
- Langfuse: `obs` profili (self-host) mi, Langfuse Cloud mu?
- Şekiller için VLM açıklaması gerekecek mi, yoksa caption yeterli mi? (Şekil sorularının eval sonucuna göre karar verilecek.)
- ~~Derlem konusu~~ → RAG / arama / LLM makaleleri (bkz. DECISIONS D8). Sıradaki CC BY adaylar: ReAct (2210.03629), Chain-of-Thought (2201.11903), vLLM/PagedAttention (2309.06180).
- OCR testi için taranmış sayfa: arXiv PDF'leri dijital; Aşama 3'te açık lisanslı, taranmış bir belge bulunacak.
