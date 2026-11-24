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

---

## Aşama 1 — Veri

### D8. Derlem konusu: RAG, arama ve LLM makaleleri
- **Karar:** İlk 5 makale: Ragas, Self-RAG, M3-Embedding (bge-m3), E5, QLoRA.
- **Neden:**
  - Projenin kullandığı tekniklerin makaleleri. Eval sorularını yazarken içeriği öğrenmiş oluyorum.
  - Yapıları farklı: kısa (Ragas, 8 sayfa) ve uzun (Self-RAG, 30 sayfa), tablo ağırlıklı (bge-m3, QLoRA), şekil ağırlıklı (Self-RAG).
  - bge-m3 ile E5 aynı konuda: "iki makale karşılaştırma" soruları için doğal bir çift.
- **Sınır:** *Attention Is All You Need*, BERT ve orijinal RAG makalesi arXiv'in varsayılan lisansında; kullanılamadı.

### D9. Lisans: yalnızca CC BY / CC0, otomatik doğrulama
- **Karar:** İndirme betiği her makalenin lisansını arXiv'in OAI-PMH arayüzünden tekrar kontrol ediyor; izin listesinde olmayanı indirmiyor.
- **Alternatif:** Lisansı elle bakıp tabloya yazmak.
- **Neden:**
  - "Açık erişim" ile "açık lisans" aynı şey değil. arXiv'in varsayılan lisansı (`nonexclusive-distrib`) yeniden dağıtıma izin vermiyor.
  - İnsan hatası olmasın diye lisans koddan doğrulanıyor.
  - CC BY-SA ve CC BY-NC de dışarıda: SA, türev işin aynı lisansla paylaşılmasını; NC, ticari olmayan kullanımı şart koşuyor. CV projesinde bu belirsizliği istemedim.
  - 18 adaydan 9'u CC BY 4.0 çıktı.

### D10. Sürüm sabitleme (arXiv `v2` gibi)
- **Karar:** `SOURCES.md`'de her makale sürümüyle yazılı (`2309.15217v2`).
- **Neden:** Eval seti "cevap sayfa 7'de" diyor. Yazarlar yeni bir sürüm yüklerse sayfalar kayar ve eval sessizce bozulur. `uv.lock` ile aynı fikir: tekrarlanabilirlik.

### D11. İndirme için standart kütüphane (`urllib`)
- **Karar:** Yeni bağımlılık eklenmedi.
- **Neden:** `httpx` `.venv`'de var ama `langchain-openai`'ın dolaylı bağımlılığı olarak geldi. `pyproject.toml`'da yazmayan bir pakete gizlice bağımlı olmak, o paket kaldırıldığında kodu kırar. Basit bir GET isteği için standart kütüphane yeterli.

---

## Aşama 2 — Eval seti

### D12. Eval-first: soruları sistemden önce yazmak
- **Karar:** 20 soru, arama sistemi yokken yazıldı ve PDF'lerle elle doğrulandı.
- **Neden:** Sistem kurulduktan sonra soru yazılırsa, farkında olmadan sistemin iyi cevapladığı sorular seçilir. Önce "iyi"nin tanımı, sonra sistem.

### D13. Doğru sonucu (makale, sayfa) ile tanımlamak
- **Karar:** Bir arama sonucu, beklenen makalenin beklenen sayfasından geliyorsa "isabet" sayılıyor. Chunk id'si kullanılmıyor.
- **Alternatif:** "Doğru cevap chunk #142'de" gibi chunk düzeyinde etiket.
- **Neden:** Chunk boyutunu defalarca değiştireceğiz. Chunk id'leri her seferinde değişir ve eval seti çöpe gider. Sayfa ise sabit (sürüm sabitlemesiyle birlikte, bkz. D10).
- **Bilinen sınırlama:** Her bilgi için tek bir kaynak sayfa tutuluyor. Bilgi başka bir sayfada da geçiyorsa (ör. q06: s.1 ve s.2), sistem doğru bilgiyi bulsa bile "kaçırdı" sayılabilir. Ölçümlerde sorun olursa şemaya "bu sayfalardan herhangi biri yeterli" seçeneği eklenecek.

### D14. Metrikler: Recall@k ve MRR (elle yazıldı)
- **Recall@k:** Beklenen kaynakların kaçı ilk k sonuçta? Karşılaştırma sorularında iki kaynak var; biri bulunduysa 0,5.
- **MRR:** İlk doğru sonucun sırasının tersi (1., 1/2, 1/3 …), soruların ortalaması. Recall "buldu mu?" diye sorar, MRR "ne kadar yukarıda buldu?" diye. LLM'e yalnızca ilk birkaç sonuç gittiği için sıra önemli.
- **Neden kütüphane yok:** Metriklerin tanımını tam olarak bilmek ve mülakatta formülünü anlatabilmek için.
- "Dokümanda yok" soruları bu metriklere girmiyor (bulunacak sayfa yok); Aşama 7'de "doğru reddetme oranı" ile ölçülecek.

### D15. Soru türleri ve tuzak sorular
- **Dağılım:** 6 tek sayfa, 4 tablo, 3 şekil, 3 karşılaştırma, 4 "dokümanda yok". Sonuçlar türe göre ayrı raporlanıyor ("tablo sorularında kötüyüz" gibi tespitler için).
- **Tuzaklar:**
  - q17'de makalede yakın ama farklı bir bilgi var (eğitim süresi var, maliyet yok).
  - q20'de cevap modelin ezberinde var (bge-m3 vektör boyutu, model kartında) ama makalede yok. Ayrıca "1024" makalede başka bir anlamda (girdi uzunluğu) geçiyor.
  - Sistem bu sorularda "Dokümanda bulamadım" demeli; doğru bir rakam bile söylese kaynaksız cevap hata sayılıyor.
- **Ders:** "Dokümanda yok" kontrolünü ilk kez metin aramasıyla yaptım ve arama aracı "1024"ü sessizce kaçırdı. Elle doğrulama bu hatayı yakaladı. "Yok" iddiası, "var" iddiasından daha zor doğrulanıyor.

---

## Aşama 3 — Ingest

### D16. PDF ayrıştırıcı: Docling (PyMuPDF değil)
- **Karar:** Docling 2.152. Ölçüm: `docs/benchmarks/parser_comparison.md` (MacBook Air M4, 5 makale, 99 sayfa).
- **Ölçümler:**

  | | PyMuPDF 2.1 | Docling 2.152 |
  |---|---|---|
  | Süre (99 sayfa) | ~12 sn | ~72 sn |
  | Beklenen 5 başlık | 4/5 | 5/5 |
  | Eval'deki 4 tablo satırı | 0/4 | 4/4 |
  | Altyazı tanıma | yok | var |
  | OCR | ayrıca Tesseract gerekir | dahili |
  | Lisans | AGPL-3.0 | MIT |

- **Neden:**
  - PyMuPDF tabloları buluyor ama içeriğini bozuyor: satırları birleştiriyor, `55.8`'i `558` ve ayrı bir `.` olarak okuyor. Tablo soruları bu çıktıyla cevaplanamaz.
  - PyMuPDF'te başlıklar PDF'in yer imlerinden geliyor; yer imi olmayan Ragas'ta 0 başlık çıktı. Docling başlıkları sayfa düzeninden tanıyor.
  - Docling'in yavaşlığı tek seferlik bir maliyet (ingest bir kez yapılıyor).
- **Bedel:** PyTorch ile ~1 GB kurulum ve model önbelleği.
- **Mülakatta:** "İki ayrıştırıcıyı eval setimin dayandığı tablo satırları üzerinde ölçtüm. PyMuPDF dört tablonun hiçbirini doğru çıkaramadı, ondalık noktaları kaybetti. Docling 6 kat yavaş ama dördünü de doğru çıkardı. Ingest tek seferlik olduğu için doğruluğu seçtim."
- **Ölçüm sırasında yakalanan hata:** İlk çalıştırmada Docling'in q08'i de kaçırdığı görünüyordu. Hata benim kontrol kuralımdaydı ("13B" tek başına bir hücre olmalı sanıyordu; hücre "Our SELF-RAG 13B" idi). Ölçüm kodunu da test etmek gerekiyor.

### D17. Ingest'i iki adıma ayırmak: parse ve chunk
- **Karar:** `ingest/parse.py` (Docling) PDF'i bizim basit öğe formatımıza (`ingest/elements.py`) çevirip `data/parsed/<makale>.jsonl` olarak kaydediyor. Chunking ayrı bir adım olacak ve bu dosyaları okuyacak.
- **Neden:**
  - Chunk ayarlarını defalarca değiştireceğiz. Parse ~70 sn sürüyor, chunking ise bir saniyeden kısa. Parse sonucu bir kez kaydedilip chunking istenildiği kadar yeniden çalıştırılabiliyor.
  - Chunking kodu Docling'e bağlı değil; testleri Docling olmadan çalışıyor.
  - Docling ileride değiştirilirse yalnızca parse adımı etkilenir.

### D18. Bağımlılık grubu: `ingest`
- **Karar:** Docling ayrı bir `ingest` grubunda. Yerelde varsayılan olarak kuruluyor (`[tool.uv] default-groups`); CI'da atlanıyor (`uv sync --no-group ingest` ve `uv run --no-sync`).
- **Neden:** Linux'ta PyTorch, GPU kütüphaneleriyle birlikte birkaç GB indiriyor; her push'ta bunu beklemek CI'ı yavaşlatırdı. Docling gerektiren testler `pytest.importorskip` ile CI'da atlanıyor.
- **Tuzak:** `uv run` çalışmadan önce ortamı varsayılan gruplara göre senkronize ediyor; CI'da `--no-sync` olmasaydı Docling yine kurulacaktı.

### D19. Parse sırasında atılan içerik
- **Sayfa üst/alt bilgileri** (her sayfada tekrar eden "Preprint.", arXiv damgası): aramada gürültü.
- **Kaynakça (References):** "BERT: Pre-training of…" gibi satırlar birçok soruya alakalı görünür ama hiçbirini cevaplamaz. Kaynakçadan sonra gelen **ekler tutuluyor** (QLoRA ve Self-RAG'in önemli tabloları orada).
- **Tablo altyazılarının ayrı kopyası:** Docling tablo Markdown'ının başına altyazıyı zaten ekliyor; ayrı altyazı öğesi de tutulsaydı 71 altyazının 48'i iki kez indekslenecekti. Şekil altyazıları ayrı öğe olarak kalıyor (şeklin altyazıdan başka metni yok).

### D20. Chunking kuralları
- **Boyut:** Hedef ~300, üst sınır 400 token (yaklaşık: kelime × 1,3). multilingual-e5-small en fazla 512 token okuyor; 400 tahmin hatasına pay bırakıyor. Aşama 4'te gerçek tokenizer ile doğrulanacak; 200 ve 500 gibi alternatifler eval ile denenecek.
  - Ölçülen veri (5 makale): paragraf ortancası 44 kelime (birleştirmek gerekiyor), en büyük tablo 738 kelime (bölmek gerekiyor).
- **Çok küçük ve çok büyük chunk'ın sorunları:** Küçük chunk bağlamı kaybeder ("it outperforms BM25": "it" kim?). Büyük chunk'ın embedding'i birçok konunun ortalaması olur ve hiçbirine net benzemez; LLM'e de alakasız metin gider ("lost in the middle").
- **Sınırlar:** Bir chunk tek bir bölümden ve tek bir sayfadan **başlar**. Paragraflar bölünmez; 400 token'ı aşan paragraf cümle sınırlarından bölünür (LangChain `RecursiveCharacterTextSplitter`, `keep_separator="end"`).
- **Tablolar:** Tek chunk. 400'ü aşarsa satır gruplarına bölünür ve her parçaya altyazı ile başlık satırı tekrar eklenir. Aksi halde `| tr | 45.8 | … | 75.6 |` satırındaki sayıların hangi sütuna ait olduğu bilinemez.
- **Contextual chunk header:** Arama metni (`search_text`) "makale başlığı > bölüm" ile başlıyor; LLM'e ve kullanıcıya giden `text` orijinal kalıyor. Örnek: e5 s.3'teki "we end up with ∼270M text pairs" paragrafında "E5" ya da "CCPairs" geçmiyor; başlık eklenmeden BM25 bu paragrafı bulamaz.
- **Örtüşme:** Yok, çünkü metin paragraf sınırlarından kesiliyor. Yalnızca uzun bir paragraf bölünürken 30 token örtüşme var.
- **Sonuç:** 362 chunk (260 metin, 74 tablo parçası, 28 şekil). Ortanca ~180 token, 400'ü aşan yok.

### D21. Kapsama kontrolü: chunking cevapları kaybetti mi?
- **Kontrol:** Cevabı olan 16 eval sorusunun her biri için, cevabın anahtar ifadesi beklenen sayfayı kapsayan bir chunk'ta var mı? Bu, aramanın ulaşabileceği üst sınır: chunking'de kaybolan bir cevabı hiçbir arama bulamaz.
- **İlk sonuç: 12/16.** İki sebep vardı:
  1. **Sayfa sonunda bölünen paragraflar (q01, q16):** Docling bir paragrafın konumunu birden fazla sayfa olarak (`[2, 3]`) veriyor; biz yalnızca ilkini kullanıyorduk. Düzeltme: Öğeler ve chunk'lar `pages` listesi taşıyor; eval'de bir chunk, beklenen sayfa bu listedeyse isabet sayılıyor. Kaynak da `s.2–3` gibi gösterilebilecek.
  2. **Şeklin içindeki yazılar (q11, q12):** Şekiller atlanıp yalnızca altyazı tutuluyordu; "summer vacation" Self-RAG Şekil 1'in içinde yazıyor. Düzeltme: Docling'in `traverse_pictures=True` ayarıyla şeklin içindeki metinler okunuyor; her şekil "altyazı + [Figure text] …" olarak tek öğe oluyor. VLM gerektirmeyen, ücretsiz bir ara çözüm.
- **Son sonuç: 16/16.**
- **Ders:** Arama kurmadan önce "cevap indekste var mı?" diye bakmak, arama hatası ile veri hazırlama hatasını birbirinden ayırıyor.
- **Açık iyileştirme:** Büyük şekiller (Self-RAG Şekil 1) bölünürken parçalara altyazı tekrar eklenmiyor; eval sonucuna göre karar verilecek.
