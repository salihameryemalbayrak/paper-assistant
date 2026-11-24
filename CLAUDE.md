# Proje: Çok Modlu Makale Asistanı (agentic RAG)

## Amaç
Açık erişimli bilgisayar/yapay zekâ makaleleri üzerinde Türkçe soru-cevap yapan, cevabı **kaynak sayfa ve bölümle birlikte** gösteren bir asistan.
Bu, yeni mezun bir mühendisin CV'sine ekleyeceği bir portföy projesi. Hedef üç şey:
- çalışan bir sistem,
- ölçülmüş sonuçlar,
- iş ilanlarında sık geçen **yaygın teknolojiler** ile kurulmuş, mülakatta derinlemesine anlatılabilir bir mimari.

Aşama aşama yol haritası: `PLAN.md`.

## Tasarım ilkesi
Zorluk modelde değil **aramada**. Hedef, küçük bir yerel model (3–4B) ile iyi sonuç almak. Projenin yıldızları hibrit arama, reranking, doğru chunking, kaynak gösterme ve eval.

## Kapsam
**Temel sürüm (öncelik):**
- PDF işleme: metin, tablo, şekil, taranmış sayfa (OCR). Sayfa ve bölüm metadata'sı korunur.
- Embedding + Qdrant, BM25 ile hibrit arama, TR→EN sorgu çevirisi, reranker.
- Kaynaklı cevap üretimi. Kaynakta yoksa "Dokümanda bulamadım." denir.
- Eval seti + otomatik metrikler.
- Langfuse ile iz kaydı.
- Docker Compose, Streamlit arayüz, FastAPI.
- GitHub Actions: ruff + pytest + hızlı eval.

**Genişletilmiş sürüm (zaman kalırsa, bu sırayla):**
- LangGraph ile agentic akış (arama, tablo okuma, belge karşılaştırma, yeniden arama kararı).
- Guardrails: kaynaksız cevabı engelleme, prompt injection testi, çıktı doğrulama.
- Küçük bir MCP sunucusu (arama aracını dışa açar).
- LoRA fine-tuning (Hugging Face PEFT, Colab).

## Teknoloji seçimleri
- **Dil ve altyapı:** Python 3.11+, FastAPI, Pydantic (`pydantic-settings`), paket yönetimi `uv` (`uv.lock` ile sabit sürümler).
- **Orkestrasyon:**
  - Temel sürüm baştan **LangChain** ile kurulur: prompt şablonları, `ChatOpenAI` (+ `base_url`), retriever'lar, zincir.
  - Agentic akış **LangGraph** ile kurulur.
  - LlamaIndex kullanılmaz (LangChain ile aynı işi yapar; ikisini birden kullanmak gereksiz).
- **Vektör DB:** Qdrant (LangChain entegrasyonu).
- **Hibrit arama:** BM25 + dense, birleştirme RRF ile.
- **Embedding / reranker:** Hugging Face `sentence-transformers` ile çok dilli, küçük modeller (ör. bge-m3 / multilingual-e5-small, bge-reranker). Seçim eval ile doğrulanır.
- **Gözlemlenebilirlik:** Langfuse (LangChain callback entegrasyonu).
- **Eval:** RAGAS + kendi Recall@k/MRR betiklerim.
- **Arayüz:** Streamlit.
- **Konteyner:** Docker Compose. Profiller:
  - `dev`: Ollama
  - `gpu`: vLLM
  - `obs`: Langfuse
- **CI:** GitHub Actions.
- LangChain API'si hızlı değişir. Sürümler sabitlenir; bir bileşenin davranışı tahmin edilmez, dokümantasyondan doğrulanır.

## Dil stratejisi (Türkçe soru, İngilizce makale)
BM25 kelime eşleşmesine dayanır; Türkçe sorgu İngilizce metinle eşleşmez. Bu yüzden arama şöyle çalışır:
- LLM soruyu İngilizceye çevirir.
- BM25 İngilizce sorguyla çalışır.
- Dense arama TR ve EN sorgularla çalışır.
- Sonuç listeleri RRF ile birleştirilir.
- Cevap Türkçe yazılır; doğrudan alıntılar orijinal dilde kalır.
- Çevirinin katkısı ve gecikme bedeli eval ile ölçülür (çeviri açık/kapalı karşılaştırması).

## Çok modluluk tanımı
- Şekiller ingest sırasında caption (+ opsiyonel küçük VLM açıklaması) ile metne çevrilir ve "şekil" tipi chunk olarak indekslenir.
- Tablolar Markdown'a çevrilip "tablo" tipi chunk olur.
- Sorgu anında görsel model çalışmaz.
- PDF ayrıştırıcı: Docling ve PyMuPDF örnek makalelerde karşılaştırılır (bölüm başlığı doğruluğu, tablo kalitesi, süre). Sonuç `docs/DECISIONS.md`'ye yazılır.

## Kaynak gösterme
- Format: `[kısa_ad, s.7, §3.2]`. Her iddia en az bir kaynağa bağlanır.
- Kaynak bulunamazsa sabit cümle: "Dokümanda bulamadım."
- Cevaptaki kaynakların gerçekten getirilen chunk'larda olduğu otomatik kontrol edilebilir olmalı.

## Model sunucusu kuralı
Kod yalnızca OpenAI uyumlu bir API'ye konuşur. Model sunucusu ortam değişkenleriyle değişir:
- `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`
- Mac'te Ollama, benchmark için vLLM, karşılaştırma için bir ticari API kullanılır; **kodda değişiklik gerektirmeden**.
- Model adı veya adres koda gömülmez.

## Ortam kısıtları
- **Ana geliştirme:** MacBook Air M4 (256 GB SSD). Diske dikkat: Docker disk sınırı koy, `ollama` modellerini temizle, büyük veriyi git'e koyma.
- **Windows makine:** RTX 3050 Ti (genelde 4 GB VRAM) + 16 GB RAM. Yalnızca küçük modeller çalışır. vLLM için WSL2 gerekir.
- **vLLM benchmark ve LoRA:** Google Colab ücretsiz katmanı. Kiralık GPU yalnızca isteğe bağlıdır (bkz. Maliyet kuralı). Sonuçlar JSON/CSV olarak repoya veya Drive'a kaydedilir.
- Docker imajları hem arm64 hem amd64'te çalışmalı.
- **Langfuse:** Self-host v3 ağırdır (Postgres, ClickHouse, Redis, MinIO). Bu yüzden ya ayrı `obs` profilinde çalışır ya da Langfuse Cloud'un ücretsiz katmanı kullanılır. `LANGFUSE_*` değişkenleri yoksa kod iz göndermeden sorunsuz çalışır.

## Maliyet kuralı
- **Varsayılan: her şey ücretsiz.** Proje hiçbir ücretli servis kullanılmadan baştan sona tamamlanabilir olmalı.
- Ücretli seçenekler (ticari LLM API'si, ücretli hakem LLM, kiralık GPU, Langfuse'un ücretli planları) yalnızca **isteğe bağlıdır** ve kullanılmadan önce bana sorulur.
- Ücretli bir API anahtarı kullanılacaksa:
  - önce sağlayıcının panelinde harcama limiti konur,
  - anahtarla bir şey çalıştırılmadan önce tahmini maliyet söylenir.
- Ücretsiz katmanlar tercih edilir: Colab ücretsiz katmanı, Langfuse self-host veya ücretsiz bulut katmanı, açık (public) GitHub reposunda Actions.

## Veri ve lisans kuralları
- Derlem 15–30 makaleden oluşur. Yalnızca **CC-BY / CC0** lisanslı makaleler kullanılır. arXiv'in varsayılan lisansı yeniden dağıtıma izin vermez; lisans makale sayfasından kontrol edilir.
- Her makalenin lisansı `data/SOURCES.md` dosyasına kaydedilir (başlık, URL, lisans).
- Ham PDF'ler ve indeks verisi git'e girmez (`.gitignore`). Veriyi indiren/işleyen betikler paylaşılır, verinin kendisi paylaşılmaz.

## Değerlendirme (eval-first)
- **Eval seti:** Küçük, elle doğrulanmış; hedef 40–60 soru (20 soruyla başlanır). Her soruda soru, beklenen cevap ve kaynak sayfa bulunur.
- **Soru türleri ve hedef dağılım:** tek sayfa (~15), tablo (~10), şekil (~8), iki makale karşılaştırma (~8), "dokümanda yok" (~8).
- **Eval iki katmanlıdır:**
  - *Hızlı eval:* Yalnızca retrieval ölçülür, LLM çağrılmaz (Recall@k, MRR). Her değişiklikte ve CI'da çalışır.
  - *Tam eval:* RAGAS ile faithfulness (cevap kaynağa sadık mı) ve answer relevancy (soruyu cevaplıyor mu). Birleştirmeden önce çalışır.
- RAGAS'ın hakem LLM'i sabit tutulur; adı her sonuçla birlikte yazılır.
- Retrieval veya prompt değişikliği ölçüm olmadan birleştirilmez.
- Rapor edilen her sayı gerçek ölçümden gelir. Ölçülmemiş sayı yazılmaz; donanım ve model adı her sonuçla birlikte belirtilir.
- **Karşılaştırma matrisi:** küçük yerel model, daha büyük açık model ve ticari API (isteğe bağlı, bkz. Maliyet kuralı); doğruluk, gecikme ve maliyet açısından karşılaştırılır.

## Çalışma kuralları (öğrenme odaklı)
Kodun tamamını sen yazarsın. Ben kodu okuyup anlayacağım, sorular soracağım ve gerekirse müdahale edeceğim. Amaç yetkinlik kazanmak ve projeyi mülakatta anlatabilmek, bu yüzden:
- Her aşamada ne yaptığını ve neden öyle yaptığını açıkla (özellikle chunking, hibrit arama, reranking, eval metrikleri, LangGraph akışı). Açıklamalar yeterince detaylı olsun; LangChain/LangGraph'ı daha önce kullanmadım.
- Hazır bir LangChain bileşeni kullandığında (ör. hibrit retriever, reranker sarmalayıcı) içeride ne yaptığını da açıkla (ör. RRF formülü, cross-encoder mantığı). "Kütüphane yapıyor" cevabı yetmez.
- Önemli tasarım tercihlerinde alternatifleri ve gerekçeyi kısaca belirt ve `docs/DECISIONS.md` dosyasına "neden bu seçim" notu olarak ekle. Bu dosya benim mülakat notum olacak.
- Hata çıktığında düzeltmeden önce nedenini anlat.
- Her aşama sonunda beni 2–3 kısa soruyla yokla (akış nasıl çalışıyor, bir parametre değişirse ne olur). Cevaplarım yanlışsa düzelt.
- Ben "bunu açıkla" veya "bunu ben yazayım" dersem o bölümde buna uy.
- Önce uçtan uca çalışan basit bir sürüm, sonra katman katman geliştirme. Gereksiz soyutlama ve erken optimizasyon yok.
- Bilmediğin bir sürüm veya API davranışını tahmin etme; dokümantasyona bak veya bana söyle.

## Kod kuralları
- Python 3.11+, tip ipuçları, `ruff` + `pytest`.
- Yapılandırma ortam değişkenleri ve tek bir ayar modülü (`app/config.py`) ile yapılır. Sırlar (API anahtarı) koda veya git'e girmez; `.env.example` güncel tutulur.
- Türkçe metin işleme: Unicode normalizasyonuna ve Türkçe karakterlere (ı, İ, ş, ğ) dikkat et; testlere Türkçe örnek ekle.
- Her adımda çalıştırılabilir bir komut ve kısa bir README bölümü bırak.
- **Dil kuralı:**
  - İngilizce: README, kod, kod yorumları, commit mesajları.
  - Türkçe: `docs/DECISIONS.md` ve `PLAN.md`.

## Repo yapısı (öneri)
```
app/            # FastAPI, retrieval, agent, LLM istemcisi, config
ingest/         # PDF işleme, OCR, chunking, indeksleme
eval/           # eval seti, metrikler, karşılaştırma betikleri
ui/             # Streamlit arayüz
infra/          # docker-compose.yml (dev/gpu/obs profilleri)
.github/        # GitHub Actions iş akışları
data/           # SOURCES.md (veri git'e girmez)
docs/           # DECISIONS.md, mimari diyagram, benchmark sonuçları
notebooks/      # Colab: vLLM benchmark, LoRA
tests/          # pytest
```

## Komutlar
Repo iskeleti oluştukça doldurulacak:

| Ne | Komut |
|---|---|
| Kurulum | `uv sync` → `cp .env.example .env` → `ollama pull qwen3:4b-instruct` |
| LLM bağlantı testi | `uv run python -m app.llm "Merhaba"` |
| Testler | `uv run pytest` |
| Lint + format kontrolü | `uv run ruff check . && uv run ruff format --check .` |
| Veri indirme | `uv run python -m ingest.download` |
| PDF ayrıştırma (Docling) | `uv run python -m ingest.parse` (`--force` ile yeniden) |
| Chunking | `uv run python -m ingest.chunk` → `data/chunks.jsonl` |
| Qdrant başlatma / durdurma | `docker compose -f infra/docker-compose.yml up -d qdrant` / `... down` |
| İndeksleme (Qdrant) | `uv run python -m ingest.index` (`--model BAAI/bge-m3` ile başka model) |
| Soru sorma (CLI) | `uv run python -m app.ask "soru"` |
| Hızlı eval (retrieval) | `uv run python -m eval.run --fast` (`--retriever bm25`, `--model ...`) |
| Cevap eval (20 soru, LLM) | `uv run python -m eval.run --answers` |
| Tam eval | _(Aşama 7)_ |
| Servisleri başlatma | _(Aşama 8)_ |

## Şimdilik yapılmayacaklar
- Ham makale PDF'lerini repoya koymak
- Eval ölçümü olmadan retrieval veya prompt değişikliği birleştirmek
- Sorgu anında görsel model (VLM) çalıştırmak
- Kimlik doğrulamalı / çok kullanıcılı arayüz
- Kubernetes, canlı demo veya bulut dağıtımı (README'de ekran görüntüsü/GIF yeterli)
- LlamaIndex
