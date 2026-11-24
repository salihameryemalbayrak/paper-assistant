# Tasarım kararları (mülakat notları)

Her karar için:
- **Karar:** ne seçtik
- **Alternatifler:** neleri düşündük
- **Neden:** neden bu seçim
- **Mülakatta:** tek cümlelik cevap

Ölçüme dayanan kararlarda sayı, donanım ve model adı birlikte yazılır.

---

## Aşama 0 — İskelet

### D1. Orkestrasyon: LangChain (LlamaIndex değil, çerçevesiz değil)
- **Karar:** LLM çağrıları, prompt şablonları ve retriever'lar için LangChain. Agentic akış için ileride LangGraph.
- **Alternatifler:**
  - **LlamaIndex:** RAG'e odaklı, indeksleme hattının çoğunu hazır veriyor.
  - **Çerçevesiz:** `openai` SDK + kendi kodum.
- **Neden:**
  - LangChain ve LangGraph iş ilanlarında en sık geçen LLM araçları.
  - LangGraph agentic akış için standart hale geldi ve LangChain ile doğal çalışıyor.
  - LlamaIndex aynı işi yapıyor; ikisini birden kullanmak "neden ikisi?" sorusunu doğurur.
  - Çerçevesiz yazmak daha öğretici olurdu ama CV'de bu anahtar kelime eksik kalırdı. Bu eksiği kapatmak için kural şu: hazır bir bileşen kullandığımızda (ör. RRF yapan retriever) içeride ne yaptığını da açıklıyoruz.
- **Mülakatta:** "LangChain'i ekosistemi ve LangGraph ile uyumu için seçtim; ama hazır bileşenlerin içini de biliyorum, örneğin hibrit aramada RRF'yi elle doğruladım."

### D2. Model sunucusu: OpenAI uyumlu API soyutlaması
- **Karar:** Kod yalnızca OpenAI API biçimini konuşur (`ChatOpenAI`). Adres, model ve anahtar ortam değişkenlerinden gelir (`LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`).
- **Alternatifler:**
  - Her sağlayıcı için ayrı istemci (Ollama'nın kendi kütüphanesi, vLLM'in kendi kütüphanesi…).
  - LangChain'in sağlayıcıya özel sınıfları (ör. `ChatOllama`).
- **Neden:**
  - Ollama, vLLM ve çoğu ticari sağlayıcı OpenAI uyumlu bir uç nokta (`/v1/chat/completions`) sunuyor.
  - Tek istemciyle Mac'te Ollama, GPU'da vLLM ve karşılaştırma için ticari API kullanılabiliyor; **kod değişmeden**, yalnızca `.env` değişerek.
  - Model karşılaştırması (Aşama 9) adil olur: aynı kod, sadece farklı model.
- **Mülakatta:** "Model sunucusunu bir ortam değişkeni haline getirdim; aynı kod Ollama'da, vLLM'de ve ticari API'de çalışıyor, bu yüzden model karşılaştırması tek değişkenli bir deney."

### D3. Paket yönetimi: `uv` + `pyproject.toml` + `uv.lock`
- **Karar:** Bağımlılıklar `pyproject.toml`'da, tam sürümler `uv.lock`'ta. Kurulum `uv sync` ile.
- **Alternatifler:** `pip` + `requirements.txt`, Poetry, conda.
- **Neden:**
  - `pyproject.toml` bugün Python'un standart proje dosyası.
  - `uv.lock` bağımlılıkların bağımlılıklarını da sabitliyor. Mac, Windows ve CI'da birebir aynı ortam kuruluyor.
  - `uv` çok hızlı ve Python sürümünü de kendisi yönetiyor.
  - Hızlı değişen LangChain gibi kütüphanelerde sürüm sabitlemek özellikle önemli.
- **Mülakatta:** "Bağımlılıkları uv ile kilitledim; CI ve diğer makinelerde aynı ortam kuruluyor, 'bende çalışıyordu' sorunu olmuyor."

### D4. Python 3.12
- **Karar:** `.python-version` = 3.12 (makinede 3.14 kurulu olmasına rağmen).
- **Neden:** PyTorch, PDF ayrıştırıcılar ve OCR gibi ağır kütüphaneler en yeni Python sürümüne genellikle gecikmeli destek veriyor. 3.12 hem modern hem geniş destekli. `uv`, 3.12'yi sistem Python'una dokunmadan ayrıca kuruyor.

### D5. Ayarlar: `pydantic-settings`
- **Karar:** Tüm ayarlar tek bir `Settings` sınıfında (`app/config.py`), ortam değişkenlerinden ve `.env`'den okunuyor.
- **Alternatifler:** Kodun içinde `os.environ[...]` dağınık kullanımı.
- **Neden:**
  - Tip kontrolü yapılıyor: yanlış değer, program açılırken anlaşılır bir hatayla yakalanıyor.
  - Zorunlu ayar eksikse program hemen duruyor.
  - API anahtarı `SecretStr` olduğu için loglara sızmıyor.
  - Tüm ayarlar tek yerde.

### D6. Metin normalizasyonu: NFC (NFKC değil) + Türkçe küçük harf
- **Karar:** `normalize_text()` NFC uygular ve PDF artıklarını (birleşik harfler, görünmez karakterler) elle düzeltir. `turkish_lower()` ise I→ı ve İ→i dönüşümlerini doğru yapar.
- **Alternatif:** NFKC. Birleşik harfleri kendiliğinden açar.
- **Neden:**
  - NFKC, makalelerde anlam taşıyan karakterleri de değiştirir (`x²` → `x2`). NFC yalnızca aynı harfin farklı kodlanışlarını birleştirir (`s` + çengel → `ş`).
  - Python'un `lower()` fonksiyonu dilden bağımsızdır: `"I".lower()` → `"i"` (Türkçede `"ı"` olmalı) ve `"İ".lower()` → `"i̇"` (iki karakter).
- **Mülakatta:** "PDF'ten gelen metinde aynı harf farklı byte'larla gelebiliyor; bunu NFC ile birleştirdim. NFKC'yi formülleri bozduğu için kullanmadım."

### D7. Maliyet: varsayılan her şey ücretsiz
- **Karar:** Proje hiçbir ücretli servis olmadan tamamlanabilir. Ticari API, kiralık GPU ve ücretli hakem model yalnızca isteğe bağlı.
- **Neden:** Projenin herkes tarafından ücretsiz olarak yeniden üretilebilmesi. Bu tasarım ilkesiyle de uyumlu: küçük yerel model + iyi arama.
