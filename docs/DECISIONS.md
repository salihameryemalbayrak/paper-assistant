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
- **Boyut:** Hedef ~300, üst sınır 400 **gerçek token** (embedding modelinin tokenizer'ı ile sayılıyor, bkz. D24). Modeller en fazla 512 token okuyor; aradaki pay önek (`passage: `), "başlık > bölüm" satırı ve özel token'lar için. 200 ve 500 gibi alternatifler eval ile denenecek.
  - Ölçülen veri (5 makale): paragraf ortancası 44 kelime (birleştirmek gerekiyor), en büyük tablo 738 kelime (bölmek gerekiyor).
- **Çok küçük ve çok büyük chunk'ın sorunları:** Küçük chunk bağlamı kaybeder ("it outperforms BM25": "it" kim?). Büyük chunk'ın embedding'i birçok konunun ortalaması olur ve hiçbirine net benzemez; LLM'e de alakasız metin gider ("lost in the middle").
- **Sınırlar:** Bir chunk tek bir bölümden ve tek bir sayfadan **başlar**. Paragraflar bölünmez; 400 token'ı aşan paragraf cümle sınırlarından bölünür (LangChain `RecursiveCharacterTextSplitter`, `keep_separator="end"`).
- **Tablolar:** Tek chunk. 400'ü aşarsa satır gruplarına bölünür ve her parçaya altyazı ile başlık satırı tekrar eklenir. Aksi halde `| tr | 45.8 | … | 75.6 |` satırındaki sayıların hangi sütuna ait olduğu bilinemez.
- **Contextual chunk header:** Arama metni (`search_text`) "makale başlığı > bölüm" ile başlıyor; LLM'e ve kullanıcıya giden `text` orijinal kalıyor. Örnek: e5 s.3'teki "we end up with ∼270M text pairs" paragrafında "E5" ya da "CCPairs" geçmiyor; başlık eklenmeden BM25 bu paragrafı bulamaz.
- **Örtüşme:** Yok, çünkü metin paragraf sınırlarından kesiliyor. Yalnızca uzun bir paragraf bölünürken 30 token örtüşme var.
- **Sonuç (gerçek tokenizer ile):** 469 chunk (297 metin, 142 tablo parçası, 30 şekil). Ortanca 227 token. 22 tablo parçası 400'ü aşıyor (en çok 457): bunlar tek bir satırı bile ~250–330 token olan geniş tablolar. Altyazı + başlık + tek satır bölünemiyor; hepsi 512'nin altında kaldığı için kabul edildi.

### D21. Kapsama kontrolü: chunking cevapları kaybetti mi?
- **Kontrol:** Cevabı olan 16 eval sorusunun her biri için, cevabın anahtar ifadesi beklenen sayfayı kapsayan bir chunk'ta var mı? Bu, aramanın ulaşabileceği üst sınır: chunking'de kaybolan bir cevabı hiçbir arama bulamaz.
- **İlk sonuç: 12/16.** İki sebep vardı:
  1. **Sayfa sonunda bölünen paragraflar (q01, q16):** Docling bir paragrafın konumunu birden fazla sayfa olarak (`[2, 3]`) veriyor; biz yalnızca ilkini kullanıyorduk. Düzeltme: Öğeler ve chunk'lar `pages` listesi taşıyor; eval'de bir chunk, beklenen sayfa bu listedeyse isabet sayılıyor. Kaynak da `s.2–3` gibi gösterilebilecek.
  2. **Şeklin içindeki yazılar (q11, q12):** Şekiller atlanıp yalnızca altyazı tutuluyordu; "summer vacation" Self-RAG Şekil 1'in içinde yazıyor. Düzeltme: Docling'in `traverse_pictures=True` ayarıyla şeklin içindeki metinler okunuyor; her şekil "altyazı + [Figure text] …" olarak tek öğe oluyor. VLM gerektirmeyen, ücretsiz bir ara çözüm.
- **Son sonuç: 16/16.**
- **Ders:** Arama kurmadan önce "cevap indekste var mı?" diye bakmak, arama hatası ile veri hazırlama hatasını birbirinden ayırıyor.
- **Açık iyileştirme:** Büyük şekiller (Self-RAG Şekil 1) bölünürken parçalara altyazı tekrar eklenmiyor; eval sonucuna göre karar verilecek.

### D22. Vektör veritabanı: Qdrant sunucusu (Docker)
- **Karar:** Qdrant ayrı bir sunucu olarak Docker'da çalışıyor (`infra/docker-compose.yml`). Veri `data/qdrant/` klasöründe (git'e girmez); konteyner silinse de indeks kalır. Portlar yalnızca `127.0.0.1`'e açık.
- **Alternatifler:**
  - Qdrant'ın gömülü modu (`QdrantClient(path=...)`): Docker gerektirmez, ama gerçek kullanımdaki istemci–sunucu yapısını göstermez ve web paneli yok. Testlerde kullanılabilir.
  - Chroma, FAISS: FAISS bir kütüphane, veritabanı değil (payload/filtre yok). Chroma da yaygın; Qdrant'ı filtreleme, hibrit (dense + sparse) arama desteği ve panelden ötürü seçtim.
- **Sürüm tuzağı:** `langchain-qdrant` 1.2.0, `qdrant-client<1.16` istiyor. İstemci, sunucuyla en fazla bir minor sürüm fark olduğunda uyumluluğu garanti ediyor. Bu yüzden Docker imajı en güncel 1.20 değil, istemciye uyan **v1.15.5**. LangChain entegrasyonu güncellenince ikisi birlikte yükseltilir.
- **Kavramlar:** *Embedding* metni anlamını temsil eden bir vektöre çevirir; *kosinüs benzerliği* iki vektörün yönüne bakar. Qdrant en yakın vektörleri tek tek karşılaştırarak değil, **HNSW** graf indeksiyle bulur (yaklaşık en yakın komşu). Her vektörün yanında bir *payload* (chunk metni, makale, sayfa, bölüm) saklanır.
- **Model başına bir koleksiyon:** e5-small 384, bge-m3 1024 boyutlu vektör üretiyor; aynı koleksiyonda karışamazlar.

### D23. Linux'ta yalnızca CPU'luk PyTorch
- **Sorun:** sentence-transformers PyTorch gerektiriyor ve artık ana bağımlılık (sorgu anında da embedding lazım). Linux'ta PyPI'daki torch, birkaç GB CUDA kütüphanesiyle geliyor; CI ve Docker imajları bunu her seferinde indirecekti.
- **Karar:** `pyproject.toml`'da `[tool.uv.sources]` ile torch, **yalnızca Linux'ta** PyTorch'un CPU deposundan (`download.pytorch.org/whl/cpu`) kuruluyor. macOS PyPI sürümünü kullanmaya devam ediyor (Apple Silicon'da GPU'yu MPS ile zaten kullanabiliyor). `uv.lock` iki sürümü de platform işaretiyle tutuyor (`2.15.0` ve `2.15.0+cpu`).
- **Ayrıntı:** uv'de `sources` yalnızca doğrudan bağımlılıklara uygulanıyor; bu yüzden `torch` listeye açıkça eklendi. `explicit = true`, bu depodan yalnızca torch'un alınmasını sağlıyor.
- **Windows (RTX 3050 Ti):** Orada GPU'lu torch istenirse ayrı bir işaretle eklenebilir. Şimdilik gerek yok, embedding modelleri CPU'da da yeterince hızlı.

### D24. Token sayımı: tahmin değil gerçek tokenizer
- **Bulgu:** İlk indekslemede `ingest/index.py`'nin kontrolü, 362 chunk'tan **29'unun modelin 512 token sınırını aştığını** gösterdi. sentence-transformers uzun metni **hata vermeden keser**: tablonun alt satırları embedding'e hiç girmiyor, aramada görünmez oluyordu.
- **Neden:** Chunking "kelime × 1,3" tahminiyle yapılmıştı. Gerçek/tahmin oranı (ortanca): metin 1,32 (tahmin doğru), şekil 1,56, **tablo 1,77**. Tablolar sayı ve sembol dolu: "0.71" bir kelime ama üç token (`0`, `.`, `71`); `|` ayrı token. Docling'in tablo hizalama boşlukları ise suçlu değildi: temizlemek yalnızca %2 kazandırıyordu (ölçüldü).
- **Karar:** Chunking, embedding modelinin tokenizer'ı ile sayıyor (`tokenizer_counter`). Sayma fonksiyonu `chunk_paper`'a parametre olarak veriliyor; testler tokenizer indirmeden kelime tahminiyle çalışıyor.
- **Model bağımlılığı:** multilingual-e5-small ve bge-m3 aynı XLM-RoBERTa tokenizer'ını kullanıyor (aynı metinde birebir aynı token'lar, doğrulandı). Bu yüzden model seçimi chunk'ları değiştirmiyor.
- **Güvenlik ağı:** `ingest/index.py` her çalıştırmada önek dahil gerçek uzunluğu ölçüp sınırı aşan chunk sayısını yazdırıyor. Düzeltmeden sonra: **0** (en uzun 491).
- **Ders:** Sessiz hatalar en tehlikelisi; varsayımlar (1,3 oranı) veri türüne göre ölçülmeli.

### D25. Retriever kavramı ve embedding modeli seçimi (baseline)
- **Retriever nedir:** LangChain'de "soru al → sıralı `Document` listesi döndür" sözleşmesi (`retriever.invoke(soru)`). `store.as_retriever(search_kwargs={"k": 10})` içeride: soruyu embedding'e çevirir (e5'te `"query: "` önekiyle), Qdrant'a en yakın 10 vektörü sorar, payload'dan `Document` kurar. Eval kodu ve cevap zinciri yalnızca bu arayüzü bilir; Aşama 5'te BM25/hibrit retriever kod değişmeden takılabilir.
- **Ölçüm:** `uv run python -m eval.run --fast [--model ...]`. 16 cevaplanabilir soru, yalnızca dense arama, Türkçe sorgu (çeviri yok), top_k=10. Apple M4, 2026-11-24. Ham sonuçlar: `docs/benchmarks/fast_eval/*.json` (soru başına sıra dahil).

| Model | Recall@1 | Recall@3 | Recall@5 | Recall@10 | MRR | Sorgu gecikmesi (ortanca) | İndeksleme (469 chunk) | Boyut |
|---|---|---|---|---|---|---|---|---|
| multilingual-e5-small | 0,375 | 0,531 | 0,594 | **0,750** | **0,509** | **22 ms** | **11 sn** | ~0,5 GB |
| bge-m3 | 0,312 | 0,594 | 0,625 | **0,750** | 0,477 | 43 ms | 303 sn | ~2,3 GB |

- **Yorum:** 16 soruda tek bir soru Recall'u 0,0625 değiştiriyor; aradaki farklar bu düzeyde, yani **anlamlı değil**. Soru bazında modeller birbirinden farklı soruları kaçırıyor (e5: q01, q12, q13; bge-m3: q11, q13, q15). Bu, ortalamaların küçük eval setinde ne kadar gürültülü olduğunu gösteriyor.
- **Karar:** Varsayılan model **multilingual-e5-small**. Doğruluk eşit, sorgu 2 kat, indeksleme ~27 kat hızlı ve model 4,5 kat küçük. Eval seti 40–60 soruya çıktığında (Aşama 7) yeniden ölçülecek.
- **Zayıf noktalar (Aşama 5–6'nın hedefi):**
  - **Şekil soruları** (e5 Recall@10: 0,33): şekil chunk'ları kısa ve dağınık metinler.
  - **Karşılaştırma soruları**: iki makaleden de chunk getirmek gerekiyor; tek bir Türkçe sorgu genelde bir makaleye yaslanıyor.
  - **Tablo soruları** iyi (1,0): soruda "Tablo 6" gibi ifadeler ve tablo altyazısı eşleşiyor.
- **Bilinen sınırlama:** Sonuç dosyaları, kod henüz commit edilmeden üretildiği için `git_commit` alanında `-dirty` işareti taşıyor.

### D26. Cevap zinciri (LCEL) ve prompt tasarımı
- **LCEL nedir:** LangChain bileşenlerinin hepsi *Runnable*: `invoke(girdi) → çıktı`. `|` operatörü bir bileşenin çıktısını sonrakine bağlar (Unix pipe gibi): `prompt | llm | StrOutputParser()`. Aynı arayüz sayesinde `stream`, `batch` ve Langfuse izleme bedavaya geliyor; retriever değiştirmek tek satır.
- **Zincir:** `RunnableParallel(docs=retriever, question=RunnablePassthrough()).assign(answer=…)`.
  - `RunnableParallel` aynı soruyu iki kola dağıtır: biri retriever'dan geçer, `RunnablePassthrough` soruyu olduğu gibi taşır → `{"docs", "question"}`.
  - `.assign(answer=…)` bu sözlüğe cevabı ekler; dokümanlar kaybolmaz. Böylece cevaptaki kaynaklar, gerçekten getirilen chunk'larla karşılaştırılabiliyor.
  - Alternatif: LangChain'in hazır `create_retrieval_chain` yardımcısı. Kullanmadım: aynı işi gizli yapıyor, açık hali hem öğretici hem kolay değiştirilir.
- **Bağlam biçimi:** Her chunk `[kısa_ad, s.X, §Y]` etiketi altında **orijinal metniyle** (`text`, `search_text` değil; bkz. D20) veriliyor. Bölüm numarası varsa `§3.2`, yoksa adı (`§Abstract`); iki sayfalı chunk `s.2–3`.
- **Prompt kuralları:** yalnızca bağlam; her iddiadan sonra etiketi aynen kopyala; cevap yoksa yalnızca "Dokümanda bulamadım."; cevap Türkçe, alıntı ve terimler orijinal dilde. Talimat İngilizce: küçük modeller İngilizce talimatı daha tutarlı izliyor.
- **Neden "bulamadım" kuralı:** Kural olmasa model bağlamda olmayan bir soruya kendi bilgisiyle (ya da uydurarak) cevap verir; kaynaklı asistanın güvenilirliği tam olarak bu sınıra dayanıyor. Eval'deki 4 "dokümanda yok" sorusu bunu ölçüyor.
- **Kaynak kontrolü:** `check_citations` cevaptaki etiketleri bağlama verilen etiketlerle karşılaştırır; bağlamda olmayan etiket = uydurulmuş kaynak. Şimdilik CLI uyarısı; Aşama 7'de metrik olacak.
- **Bağlam boyutu:** İlk 5 chunk (~1.200 token). Hızlı eval'de Recall@5 = 0,59: bazı sorularda doğru chunk bağlama girmiyor. Reranker (Aşama 6) bunu hedefliyor.

### D27. LLM: qwen3:4b yerine qwen3:4b-instruct
- **Bulgu (Apple M4, Ollama 0.40.18):** qwen3:4b "hibrit" model: aynı ağırlıklarla "düşünen" ve "düşünmeyen" modlarda çalışabiliyor. Varsayılan modda "2+2 kaç?" için **2.892 token gizli düşünme, 88 sn**; cevap tek kelime. `/no_think` ekiyle bile 637 token, 18 sn.
- **Kapatma denemeleri** (OpenAI uyumlu API üzerinden):
  - `think: false`: yok sayıldı (2.591 token, 99 sn).
  - `reasoning_effort: "none"`: düşünme ayrı alana gitmedi, **cevabın içine** yazıldı ("Okay, so the user is asking…").
  - Sonuç: güvenilir değil; süre de soruya göre 10–99 sn arasında oynuyor.
- **Karar:** Aynı ailenin yalnızca talimat izleyen sürümü **qwen3:4b-instruct** (Qwen3-4B-Instruct-2507, 2,5 GB). Kod değişmedi; yalnızca `LLM_MODEL` ortam değişkeni (model sunucusu kuralının faydası).
- **Neden RAG için yeterli:** Burada model akıl yürütmüyor, verilen bağlamı özetleyip kaynak gösteriyor. Düşünme modu bu iş için gecikmeye değmez. "Düşünen" model ile karşılaştırma Aşama 9'daki matrise eklenebilir.

### D28. İlk uçtan uca sonuç ve "doğru sayfa ≠ doğru chunk" dersi
- **Ölçüm:** `uv run python -m eval.run --answers`. qwen3:4b-instruct (Ollama, Apple M4), e5-small, yalnızca dense, Türkçe sorgu, bağlamda 5 chunk. Sonuç dosyası: `docs/benchmarks/answers/2026-11-24_qwen3_4b_instruct.json`.

| Ölçüt | Sonuç |
|---|---|
| Doğru reddetme ("dokümanda yok" soruları) | **4/4** |
| Uydurulmuş kaynak etiketi | **0** |
| Kaynak etiketi olmayan cevap | **0** |
| Yanlış reddetme (cevaplanabilir sorular) | 6/16 |
| Soru başına süre (ortanca) | 5,9 sn |

- **Yanlış reddetmelerin nedeni aramada, modelde değil:**
  - q11, q13, q15: beklenen sayfa ilk 5 chunk'ta yok. Bağlamda cevap olmadığı için "bulamadım" demek **doğru davranış**.
  - q08, q09: beklenen sayfa bağlamda, ama **yanlış chunk**. Sayılar tablo chunk'ında (self_rag-0059, bge_m3-0049); getirilen ise aynı sayfada tabloyu anlatan paragraflar. Model sayıyı uydurmak yerine reddetti: istenen davranış.
  - q02: getirilen chunk eğitimin sonrasını anlatıyor; veri toplama yöntemi komşu chunk'ta.
- **Ders: sayfa düzeyindeki Recall iyimser.** Eval sayfa düzeyinde tanımlı (D12): aynı sayfadaki herhangi bir chunk isabet sayılıyor. Tablo ile onu anlatan paragraf aynı sayfada olduğunda metrik "buldu" diyor, model ise cevabı göremiyor. Sayfa düzeyi yine doğru seçim (chunking değişince eval seti bozulmuyor), ama yorumlanırken bu sınır bilinmeli. Olası ek ölçüt: cevabın anahtar ifadesini içeren chunk'ın getirilip getirilmediği (D21'deki kapsama kontrolünün arama versiyonu).
- **Sonraki aşamaların hedefi:** Tablo ve şekil chunk'ları birebir kelime eşleşmesiyle bulunur ("Table 2", "PopQA", "Recall@100", "Figure 1"). Bu, BM25 ve İngilizce sorgu çevirisinin (Aşama 5) tam olarak çözmesi beklenen sorun. Aynı 20 soru ile yeniden ölçülecek.
- **Gözlem:** q12'de cevap doğru ama kaynak olarak beklenen Şekil 1 (s.1) yerine s.9'daki "Ethics Consideration" paragrafı gösterildi. Etiket bağlamda var (uydurma değil), ama asıl kaynak değil. Faithfulness bunu ölçmez; kaynak doğruluğu Aşama 7'de ayrıca ele alınacak.

### D29. BM25: kendi retriever sınıfımız, birleştirme için EnsembleRetriever
- **Karar:** BM25 için `app/bm25.py` içinde kendi `BM25Retriever` sınıfımız (LangChain `BaseRetriever` arayüzü, puanlama `rank-bm25`). Sonuç listelerinin RRF ile birleştirilmesi LangChain'in `EnsembleRetriever`'ı ile (Aşama 5c).
- **Neden hazır BM25Retriever değil:** `langchain-community` paketinde; paket "sunset" (bakımı bırakılıyor) uyarısı veriyor. Ayrıca varsayılan kelime ayırıcısı `text.split()`: "BM25," ile "bm25" farklı kelime sayılıyor.
- **EnsembleRetriever ne yapar, ne yapmaz:** Kendisi arama yapmaz; verilen retriever'ların listelerini toplar, her chunk'a `ağırlık / (60 + sıra)` puanı verip toplar, aynı chunk'ı `id_key` ile tekilleştirir. BM25 retriever'ına ihtiyaç duyar; onun yerine geçmez. Retriever'ları sırayla çalıştırır ve hepsine aynı girdiyi verir (kaynak kodundan doğrulandı).
- **Kelime ayırıcı:** küçük harf; `recall@100`, `55.8`, `bge-m3` tek parça; noktalama atılır; scikit-learn'ün İngilizce stopword listesi. Kök bulma (stemming) yok, ayrıca denenebilir.
  - Stopword'ler neden şart: makale metinlerinde "what/does/how" nadir geçtiği için idf'leri yüksek (3–4) çıkıyordu ve BM25'i alakasız paragraflara yönlendiriyordu. Çıkarınca deneme sorgusunda q09'un cevap chunk'ı 48. sıradan 11.'ye çıktı.
  - Türkçe tuzak: Küçük harfe çevirme İngilizce kuralla yapılıyor (`turkish_lower` "IDF"yi "ıdf" yapardı). Ama Python `"İ".lower()` sonucu `i` + birleşik nokta (U+0307) veriyor ve kelimeyi bölüyor; bu yüzden önce `İ → i` dönüşümü yapılıyor. Testle sabitlendi.
- **BM25 formülü (rank-bm25, k1=1,5, b=0,75):** `Σ idf(w) · f·(k1+1) / (f + k1·(1 − b + b·|D|/ort_uzunluk))`, `idf = ln((N − n + 0,5)/(n + 0,5))`. k1 doygunluk (aynı kelimenin tekrarı az ödüllendirilir), b uzunluk düzeltmesi.
  - Okapi sınırı: Chunk'ların yarısından fazlasında geçen kelimenin idf'si ≤ 0. Böyle kelimeler tek başına eşleşme sağlamaz; çok küçük derlemlerde (testler) beklenmedik boş sonuç verir.
  - Puanı 0 olan chunk döndürülmüyor: dense her zaman k sonuç verir, BM25 vermemeli; yoksa RRF alakasız chunk'lara sıra puanı dağıtır.
- **İndeks:** Bellekte, başlangıçta `data/chunks.jsonl`'dan kuruluyor (469 chunk, milisaniyeler). Dense ile aynı `search_text` indeksleniyor; aynı chunk iki listede aynı `chunk_id`'yi taşıyor.
- **Alternatif: Qdrant'ın kendi hibrit araması** (fastembed `Qdrant/bm25` seyrek vektörleri + sunucu tarafında RRF). Ölçeklenme yolu bu (milyonlarca belge, kalıcı indeks). İncelenen tuzaklar:
  1. `langchain-qdrant` koleksiyonu `modifier=IDF` olmadan kuruyor: IDF'siz kelime sayımı olur, sessizce kötü sonuç verir.
  2. Hibrit mod dense ve seyrek aramaya aynı sorguyu veriyor; bizim TR/EN tasarımı için `qdrant-client` ile özel sorgu yazmak gerekir.
  3. fastembed kelime ayırıcısı `55.8`'i `55` ve `8`, `Recall@100`'ü `recal` ve `100` diye bölüyor (kök bulma ise var).

### D30. BM25'in Türkçe sorguyla ilk ölçümü: dense ile birbirini tamamlıyor
- **Ölçüm:** `uv run python -m eval.run --fast --retriever bm25`. Çeviri yok, Türkçe sorgu. Apple M4.

| Retriever | Recall@1 | Recall@5 | Recall@10 | MRR | Gecikme |
|---|---|---|---|---|---|
| dense (e5-small) | 0,375 | 0,594 | 0,750 | 0,509 | 22 ms |
| BM25 | 0,375 | 0,562 | 0,750 | 0,485 | 0,4 ms |

- **Beklenmeyen sonuç:** Türkçe sorgu İngilizce metinde BM25 ile hiç eşleşmez sanılıyordu. Eşleşiyor, çünkü sorular İngilizce terimlerle dolu: "Ragas", "Self-RAG", "PopQA", "MKQA", "M3-Embedding", "faithfulness", "QLoRA". Bunlar tam BM25'in güçlü olduğu nadir, özel kelimeler.
- **Birbirini tamamlama:** Dense'in ilk 10'da bulamadığı q01, q12, q13'ü BM25 4., 1., 1. sırada buluyor; BM25'in bulamadığı q05, q11, q15'i dense 2., 6., 9. sırada buluyor. İkisinden en az biri **16/16** soruyu ilk 10'da buluyor. RRF ile birleştirme (5c) için güçlü bir gerekçe.
  - BM25'in kaçırdıkları terimsiz, tamamen Türkçe anlatımlı sorular (q05: "sorgu ile pasajı ayırt etmek için hangi önek"; q11: "yaz tatili" örneği). Dense'in kaçırdıkları ise özel ad/şekil numarası içerenler.
- **Eval seti uyarısı:** Sorulardaki İngilizce terim yoğunluğu BM25'i kolaylaştırıyor olabilir. Gerçek kullanıcılar da yapay zekâ konularında İngilizce terim kullanıyor, ama eval seti genişletilirken (Aşama 7) terimsiz, doğal Türkçe sorular da eklenmeli. Çevirinin (5b) katkısı en çok bu tür sorularda görülmeli.

### D31. Hibrit arama (dense + BM25, RRF): ilk ölçüm
- **Kurulum:** `app/retrieval.py`. `EnsembleRetriever(retrievers=[dense, bm25], weights=[0.5, 0.5], c=60, id_key="chunk_id")`; iki listenin her biri k sonuç getiriyor, birleşik liste ilk k'ya kısaltılıyor. Retriever `.env`'den seçiliyor: `RETRIEVER=dense|bm25|hybrid`.
- **RRF örneği:** İki listede de 2. olan chunk: `0,5/62 + 0,5/62 = 0,0161`. Yalnızca bir listede 1. olan: `0,5/61 = 0,0082`. RRF **uzlaşmayı** ödüllendiriyor: iki yöntemin birlikte beğendiği chunk, tek bir yöntemin şampiyonunu geçiyor.
- **Hızlı eval (Türkçe sorgu, çeviri yok, Apple M4):**

| Retriever | Recall@1 | Recall@3 | Recall@5 | Recall@10 | MRR |
|---|---|---|---|---|---|
| dense | 0,375 | 0,531 | 0,594 | 0,750 | **0,509** |
| BM25 | 0,375 | 0,500 | 0,562 | 0,750 | 0,485 |
| hybrid | 0,375 | 0,469 | **0,625** | **0,812** | 0,487 |

- **Cevap eval (qwen3:4b-instruct, bağlamda 5 chunk):**

| | dense | hybrid |
|---|---|---|
| Doğru reddetme | 4/4 | 4/4 |
| Tam cevap (16 cevaplanabilir soru) | 10 | 9 |
| Kısmi cevap (içerik + "bulamadım") | 0 | 2 (q14, q16) |
| Reddetme | 6 | 5 |
| Geçersiz kaynak etiketi | 0 | 1 (q14: model `bge_m3` yerine `bge_m-3` yazdı) |

- **Yorum:** Hibrit, ilk 10'da daha çok doğru sayfa getiriyor (Recall@10 +0,06), ama ilk 5'te fark küçük ve cevap kalitesine yansımıyor. RRF uzlaşmayı ödüllendirdiği için yalnızca bir yöntemin bulduğu chunk'lar (q11: yalnızca dense, 6. sıra) geriye düşüyor; "ikisinden biri 16/16 buluyor" üst sınırına ulaşılamıyor.
- **Karar:** Varsayılan retriever şimdilik **dense** kalıyor (ölçülmüş bir iyileşme yok). Hibritin asıl değeri reranker ile birlikte bekleniyor (Aşama 6): reranker ilk 10–20 adayı yeniden sıralar, bu yüzden aday havuzunun genişliği (Recall@10/20) önemli; hibrit tam bunu artırıyor.
- **Ölçümde düzeltilen iki hata:**
  1. "Reddetme" sayımı, cevabın içinde "Dokümanda bulamadım." geçmesine bakıyordu. Model bazen önce kısmi cevap verip sonuna bu cümleyi ekliyor; bunlar reddetme sayılıyordu. Artık üç tür var: `answer`, `partial`, `refusal`. Kayıtlı iki sonucun özeti, LLM yeniden çalıştırılmadan saklanan cevaplardan yeniden hesaplandı.
  2. Kaynak etiketi düzeltme fonksiyonu her tireyi uzun tireye çeviriyordu (`bge_m-3` → `bge_m–3`); artık yalnızca sayfa aralıklarına uygulanıyor.
  3. (Süreç) `--answers` sonuç dosyasının adında retriever yoktu; hibrit sonuç dense sonucunun üstüne yazıldı. Dense sonuç git'ten geri alındı, dosya adına retriever eklendi.
- **Görülen model hatası (sayımların yakalamadığı):** Karşılaştırma sorularında 4B model iki makalenin bilgilerini karıştırıyor (q14: M3'ün [CLS] yöntemini E5'e; q16: QLoRA bulgularını Ragas'a mal ediyor). Etiket geçerli, iddia yanlış. Bunu RAGAS faithfulness ölçümü yakalamalı (Aşama 7); daha büyük model karşılaştırması Aşama 9.

### D32. TR→EN sorgu çevirisi ve varsayılan retriever: dense(TR) + BM25(EN)
- **Çeviri zinciri:** `app/translate.py`, LCEL ile `prompt | LLM | metin`. Ardından temizleme adımı: "Translation:" etiketi, tırnaklar ve açıklama satırları atılır. Çıktı boşsa orijinal soru kullanılır (çeviri başarısız olsa da arama çalışır).
  - **Temperature 0:** Her adımda en olası token seçilir. Aynı soru her seferinde aynı çeviriyi verir; eval tekrarlanabilir kalır.
  - **Prompt kuralları:** Teknik terimler, model/veri seti adları ve sayılar aynen kalır. "Tablo 6" → "Table 6". Zaten İngilizce olan soru değiştirilmez. Bunun için sezgisel bir "Türkçe karakter var mı" kontrolü yerine modele güveniliyor: "E5 modeli neyi ölçer" sorusunda hiç Türkçe karakter yok.
- **Eval için kayıtlı çeviriler:** `eval/translations.jsonl` (`uv run python -m eval.translations`). Hızlı eval LLM çağırmaz; her koşu aynı çevirileri kullanır, böylece Recall farkı çeviri rastlantısından değil retriever'dan gelir.
  - Alanlar: `en` modelin ham çevirisi, hiç değiştirilmez (gerçek sistemin göreceği budur); `en_fixed` insan düzeltmesi; `reviewed`.
  - Önlemler: Dosya varsa `--force` olmadan yeniden üretilmez (insan kontrolü silinmesin). Yükleyici, Türkçe soru sonradan değiştiyse "çeviri eski" diye hata verir.
  - 20 sorunun 20'si çevrildi, ortanca 0,83 sn (en fazla 1,69 sn), qwen3:4b-instruct, Apple M4.
  - Kontrol bulguları:
    - **q11 yanlış:** "deneme" → "trial" (doğrusu "essay"; "trial" Self-RAG'de 0 kez geçiyor).
    - **q07, q16:** Türkçe "uyum" → "alignment". Ragas makalesi "agreement" diyor; "alignment" 0 kez geçiyor. Bu çeviri hatası değil, **kelime uyuşmazlığı** (vocabulary mismatch): soran kişi makalenin hangi kelimeyi seçtiğini bilemez. BM25'i yapay olarak kolaylaştırmamak için düzeltilmedi.
- **Tasarım: önce çevir, sonra dağıt.** Retriever girdisi `{"tr": ..., "en": ...}` sözlüğü. Çeviri bir kez yapılır; her kol `itemgetter("tr"|"en")` ile kendi dilini alır. Varyantlar kodda bir tablo olarak tutuluyor (`BRANCHES`: varyant → (dil, motor) listesi). Aynı motor birden fazla kolda kullanılırsa bir kez kurulup paylaşılıyor.
  - `EnsembleRetriever.invoke` girdiyi `str` diye tipliyor, ama kaynak koduna göre (langchain-classic 1.1.0, `rank_fusion`) girdiyi değiştirmeden her kola iletiyor. Sözlük girdisi bu davranışa dayanıyor; bir testle sabitlendi (`test_ensemble_passes_a_dict_query_unchanged`). Yeni bir sürüm girdiyi dönüştürürse test kırılır.
  - Çevirisiz varyantlarda sorgu yalnızca `{"tr"}`; LLM boşuna çağrılmaz. Çevirili bir varyant `"en"`yi bulamazsa `KeyError` ile hata verir, sessizce Türkçe soruyla aramaz.
- **Hızlı eval** (16 cevaplanabilir soru, e5-small, kayıtlı çeviriler, Apple M4; gecikmeye çeviri dahil değil):

| Varyant | Kollar | R@1 | R@3 | R@5 | R@10 | MRR | Gecikme |
|---|---|---|---|---|---|---|---|
| dense | dense(TR) | 0,375 | 0,531 | 0,594 | 0,750 | 0,509 | 22 ms |
| bm25 | BM25(TR) | 0,375 | 0,500 | 0,562 | 0,750 | 0,485 | 0,6 ms |
| hybrid | dense(TR) + BM25(TR) | 0,375 | 0,469 | 0,625 | 0,812 | 0,487 | 21 ms |
| dense_en | dense(EN) | 0,312 | 0,562 | 0,688 | 0,844 | 0,492 | 19 ms |
| bm25_en | BM25(EN) | **0,469** | 0,656 | 0,750 | **0,906** | **0,646** | 0,5 ms |
| dense_tr_en | dense(TR) + dense(EN) | 0,438 | 0,562 | 0,656 | 0,812 | 0,552 | 43 ms |
| hybrid_en | dense(TR) + dense(EN) + BM25(EN) | 0,375 | 0,656 | 0,719 | 0,844 | 0,556 | 44 ms |
| **dense_tr_bm25_en** | dense(TR) + BM25(EN) | 0,375 | **0,719** | **0,781** | 0,844 | 0,563 | 22 ms |

  - Eski üç varyant, refactor sonrası dünküyle birebir aynı sayıları verdi: yeni yapı davranışı değiştirmedi.
- **Bulgu 1: çevirinin en büyük katkısı BM25'e.** MRR 0,485 → 0,646. İlk 10'da bulunamayan soru kalmadı. Kelime eşleşmesi makalenin dilinde sorulunca çalışıyor; CLAUDE.md'deki dil stratejisinin gerekçesi ölçümle doğrulandı.
- **Bulgu 2: yanlış tahmin.** q11'deki "trial" hatasının BM25'i bozacağını tahmin etmiştim; bm25_en q11'i 1. sırada buldu. Sorgudaki diğer kelimeler (Self-RAG, Figure 1, vacation, prompt) tek kelimelik hatayı telafi etti. BM25 tek bir kelimeye değil, kelimelerin toplamına bakar.
- **Bulgu 3: kol sayısı = oy sayısı.** hybrid_en, bm25_en'den kötü. Eşit ağırlıklı üç kolda dense fiilen 2/3 oy alıyor. q13'te BM25(EN) doğru chunk'ı 1. sırada buluyor, iki dense kol hiç bulamıyor:
  - Doğru chunk (yalnız BM25'te 1.): `1/3 · 1/61 = 0,0055`
  - İki dense listede 5. olan yanlış chunk: `2 · 1/3 · 1/65 = 0,0103`
  - Sonuç: BM25'in "eminim" sinyali bastırılıyor (D31'deki "tek listede bulunanı geriye itme" sorununun güçlü hâli). Çözüm, ağırlık denemek değil, gerekçesi önceden belli bir varyant: **her motor kendi en iyi dilinde, birer oy** (dense TR + BM25 EN). q13 hybrid_en'de bulunamıyordu, bu varyantta 5. sırada.
  - Ağırlıkları 16 soruda deneyerek ayarlamak bilinçli olarak yapılmadı: bu sorulara uyan, yenilerinde işe yaramayan bir ayar bulunurdu (aşırı uyum).
- **Cevap eval** (qwen3:4b-instruct, bağlamda 5 chunk, çeviri canlı ve gecikmeye dahil, Apple M4):

| | dense | hybrid | bm25_en | **dense_tr_bm25_en** |
|---|---|---|---|---|
| Doğru reddetme | 4/4 | 4/4 | 4/4 | 4/4 |
| Tam cevap (16) | 10 | 9 | 11 | **13** |
| Kısmi | 0 | 2 | 1 | 0 |
| Reddetme | 6 | 5 | 4 | 3 |
| Kaynak bağlamdaydı ama reddetti | — | — | 3 | 2 (q08, q09) |
| Geçersiz etiket | 0 | 1 | 0 | 0 |
| Gecikme (ortanca) | 5,9 sn | 5,6 sn | 6,5 sn | 7,8 sn |

  - dense_tr_bm25_en cevapları beklenen cevaplarla elle karşılaştırıldı:
    - **10 doğru:** q01, q03–q07, q10, q11, q13, q16. q16 dün makaleleri karıştırıyordu, şimdi doğru.
    - **1 eksik:** q02.
    - **2 yanlış:** q12 (üç "Multi"den biri yanlış), q14 (E5'in average pooling'ini söylemiyor). Bunlar model hatası, arama hatası değil.
  - Bu elle kontrol yalnızca bu varyant için yapıldı; dünkü dense cevapları aynı titizlikle okunmadı. Otomatik doğruluk ölçümü Aşama 7'de (RAGAS).
- **Karar:** Varsayılan `RETRIEVER=dense_tr_bm25_en`. İlk 5'te en iyi Recall (0,781) bu varyantta; LLM'e 5 chunk verildiği için en önemli metrik bu. Cevap sayısı da aynı yönü gösteriyor (10 → 13).
  - **Bedeli:** Soru başına ~1,9 sn daha uzun. ~0,8 sn'si çeviriden, gerisi daha çok soruya (daha uzun) cevap verilmesinden geliyor.
  - **Sınırlar:**
    - 16 soru az; farkların çoğu 1–2 soruluk.
    - Eval seti İngilizce terim ağırlıklı ve bu BM25'i kolaylaştırıyor (D30).
    - Anlam sorularında (q05, q15) dense hâlâ daha iyi; bu yüzden dense kol tutuluyor.
  - Aşama 7'de eval seti 40–60 soruya çıkınca yeniden ölçülecek. Reranker (Aşama 6) bu varyantın aday listesi üzerine kurulacak.
- **Süreç düzeltmesi:** Aynı gün aynı varyant iki kez çalıştırılınca sonuç dosyası üzerine yazılıyordu. Artık `unique_path` dosya varsa `_2`, `_3` ekliyor (CLAUDE.md: eski sonuç asla ezilmez).

### D33. Reranker (cross-encoder): arama ölçümleri iyileşti, cevaplar iyileşmedi; varsayılan kapalı
- **Bi-encoder ile cross-encoder farkı:**
  - **Bi-encoder** (dense arama, e5): Soru ve chunk ayrı ayrı vektöre çevrilir. Chunk vektörleri ingest'te bir kez hesaplanır; arama hızlıdır, ama iki metin birbirini hiç "görmez", bütün anlam tek bir vektöre sıkışır.
  - **Cross-encoder:** Soru ve chunk transformer'a birlikte girer (`[soru] [SEP] [chunk]`). Dikkat (attention) katmanları sorudaki her kelimeyi chunk'taki her kelimeyle karşılaştırır, model tek bir alaka puanı verir. Daha isabetlidir, ama önceden hesaplanacak bir şey yoktur: her (soru, chunk) çifti için model baştan çalışır.
- **Neden iki aşama:** 469 chunk'ın hepsini cross-encoder'dan geçirmek, soru başına 469 model çalıştırması demek. Bu yüzden önce hızlı arama 20 aday getirir (önemli olan Recall: doğru chunk 20'nin içinde mi?), sonra cross-encoder yalnızca bu 20 adayı sıralar (önemli olan doğru chunk'ın ilk k'ya girmesi).
- **LangChain'de ne kullanıldı** (langchain-classic kaynak kodundan kontrol edildi):
  - `CrossEncoderReranker`: Her aday için `(soru, page_content)` çifti kurar, `model.score(çiftler)` ile puanlatır, büyükten küçüğe sıralar ve ilk `top_n`'i döndürür. Kullanıldı.
  - Model sarmalayıcısı `HuggingFaceCrossEncoder` yalnızca `langchain-community`'de var (kullanılmıyor, D29). Bu yüzden `langchain_core.cross_encoders.BaseCrossEncoder` arayüzüyle kendi sarmalayıcımız yazıldı (`app/rerank.py`, içinde sentence-transformers `CrossEncoder`).
  - `ContextualCompressionRetriever` kullanılmadı: aynı sorguyu hem retriever'a hem reranker'a veriyor. Bizim sorgumuz `{"tr","en"}` sözlüğü, reranker'a ise tek bir dilde metin gerekiyor. Yerine 3 satırlık LCEL: adayları getir, `query[dil]` ile yeniden sırala.
  - Puanlar sigmoid'den geçmiş ya da ham logit olabilir; sıralama değişmez, çünkü sigmoid tekdüze (monoton) artan bir fonksiyon.
- **Karşılaştırılan iki reranker** (bilgiler Hugging Face'ten):
  - `bge_m3`: `BAAI/bge-reranker-v2-m3`, Türkçe soruyla. 568M parametre, çok dilli, Apache-2.0, ~2,3 GB.
  - `minilm_en`: `cross-encoder/ms-marco-MiniLM-L6-v2`, İngilizce çeviriyle. 23M parametre, yalnızca İngilizce, Apache-2.0, ~90 MB.
  - Bu karşılaştırmanın sorduğu soru: "Çeviri varken büyük, çok dilli bir reranker'a gerek var mı?"
- **Sessiz kesme bulundu ve düzeltildi:**
  - MiniLM'in azami uzunluğu 512 token. En uzun soruyla birlikte **142 tablo chunk'ının 94'ü** bu sınırı aşıyordu (en uzun çift 1538 token); model tabloların alt satırlarını hiç görmeden puanlayacaktı.
  - Neden: Docling'in hizalı Markdown tabloları (`|----------|`). BERT'in WordPiece tokenizer'ı her tireyi ayrı bir token sayıyor; e5'in SentencePiece tokenizer'ı tire dizisini birleştiriyor. Chunk boyutunu e5'e göre ayarlamıştık (D24); **token sınırı modele özgüdür.**
  - Çözüm: Yalnızca reranker girdisinde tablo dolgusu sıkıştırılıyor (`compact`: 3'ten uzun tire dizisi → `---`, çoklu boşluk → tek boşluk). İndekse dokunulmadı. Sonrasında sınırı aşan çift sayısı MiniLM'de 94'ten 0'a, bge'de 4'ten 0'a indi (bge'nin sınırı 8192 olduğu için onda zaten kesme yoktu).
  - Sarmalayıcı sınırı aşan çiftleri sayıyor; sayı eval sonuç dosyasına yazılıyor (`reranker_counts`). Bu koşularda 340 çiftin 0'ı.
- **Hızlı eval** (16 cevaplanabilir soru, retriever `dense_tr_bm25_en`, 20 aday → ilk 10, Apple M4; bge MPS üzerinde float32):

| Reranker | R@1 | R@3 | R@5 | R@10 | MRR | Gecikme (çeviri hariç) |
|---|---|---|---|---|---|---|
| yok | 0,375 | 0,719 | 0,781 | 0,844 | 0,563 | 22 ms |
| bge_m3 (TR) | **0,562** | 0,656 | **0,812** | 0,906 | 0,670 | 2695 ms |
| minilm_en (EN) | 0,531 | **0,781** | 0,781 | 0,906 | **0,706** | 140 ms |

  - Her iki reranker da q01'i kurtardı: q01 reranker'sız ilk 10'da yoktu ama 20 adayın içindeydi.
  - Güçlü yanları farklı: bge şekil sorularının üçünü de 1. sıraya koydu; minilm tek sayfalık sorularda R@3 = 1,00 yaptı.
  - Reranker her zaman iyileştirmiyor: bge q05'i 2. sıradan 9.'ya, minilm q12'yi 3.'den 6.'ya düşürdü.
- **Cevap eval** (qwen3:4b-instruct, bağlamda 5 chunk, çeviri canlı; aynı gün, Apple M4):

| | reranker yok | bge_m3 | minilm_en |
|---|---|---|---|
| Doğru reddetme | 4/4 | 4/4 | 4/4 |
| Cevaplanan / kısmi / reddedilen (16) | 13 / 0 / 3 | 10 / 2 / 4 | 12 / 0 / 4 |
| **Doğru** (elle, beklenen cevapla) | **10** | **10** | **7** |
| Gecikme (ortanca) | 8,2 sn | 12,3 sn | 9,8 sn |

  - **Tekrarlanabilirlik kontrolü:** Reranker'sız koşu bugün yeniden çalıştırıldı; 20 cevabın 20'si dünküyle birebir aynı (temperature 0). Gecikme 7,8 sn'den 8,2 sn'ye çıktı; karşılaştırma aynı günün sayısıyla yapıldı.
  - Doğruluk elle sayıldı, tek koşu. Sayılara q02 (yüzeysel) ve minilm'in q16'sı (belirsiz) dahil değil. Kısmi cevaplar içerik doğruysa doğru sayıldı (bge q16).
  - **Kazanılanlar:** bge q12'yi düzeltti (baseline'da üç "Multi"den biri yanlıştı) ve q02'ye daha ayrıntılı cevap verdi.
  - **Kaybedilenler:**
    - q05 (bge): Doğru chunk ilk 5'ten düştü; model reddetti. Bağlamda kaynak olmadığı için davranış doğru, hata reranker'ın.
    - q12 (minilm): Aynı durum; Şekil 1 chunk'ı ilk 5'ten düştü.
    - q11 (ikisinde de): Kaynak bağlamda, ama reranker'ın öne çıkardığı "retrieval nasıl çalışır" chunk'ları modeli yanılttı. Model "retrieval yapmıyor" yerine arama sürecini anlattı.
    - q10 (minilm): Yanlış sayı (%87,0 yerine %64,4); bağlama giren başka bir tablo satırından.
  - **Gecikme:** minilm +1,6 sn, bge +4,1 sn. Bunun 0,14 ve 2,7 sn'si reranking'in kendisi. Kalan ~1,4 sn'nin nedeni ölçülmedi; bağlamlar ~%10 uzadı (ortanca 4168 → ~4570 karakter), reranker ile Ollama aynı GPU belleğini paylaşıyor olabilir.
- **Neden arama iyileşti ama cevaplar iyileşmedi (mülakat notu):**
  1. LLM'e 5 chunk gidiyor; R@5 neredeyse hiç değişmedi (minilm 0,781 → 0,781). Reranker ilk 5'in **içindeki sırayı** değiştirdi; LLM için sıra pek önemli değil.
  2. Ölçüt sayfa düzeyinde (D28): Aynı sayfanın yanlış chunk'ı da isabet sayılıyor. Reranker'ın "konuyla ilgili ama cevabı içermeyen" chunk'ları öne çıkarması Recall'da görünmüyor, cevapta görünüyor (q11).
  3. 4B model dikkat dağıtıcı chunk'lara karşı hassas: Bağlamdaki her chunk "alakalı görünür" hâle gelince yanlış olanı seçebiliyor.
  4. Karşılaştırma soruları (q14–q16, R@5 0,17–0,33) bir sıralama sorunu değil, çeşitlilik sorunu: Cross-encoder her chunk'ı tek tek puanlar, ilk 5 tek makaleden gelebilir. → G1 (LangGraph) belge karşılaştırma aracı.
- **Karar:** Varsayılan **`RERANKER=` (kapalı)**. Ölçülmüş bir cevap kazancı yok; minilm doğruluğu düşürdü, bge 4 sn ekliyor. Kod ve iki reranker seçeneği kalıyor (`RERANKER=bge_m3|minilm_en`).
  - İki reranker arasında bge daha güvenli: doğrulukta baseline ile berabere, minilm'den 3 doğru fazla. Ama 19 kat yavaş.
  - **Sınırlar:** 16 soru, elle doğruluk, tek koşu; farkların çoğu 1–3 soru.
  - **Yeniden ölçülecek:**
    - Aşama 7: 40–60 soru, RAGAS faithfulness ve chunk düzeyinde bir alaka ölçütü.
    - Aşama 9: daha büyük LLM. Daha güçlü bir model, daha iyi sıralanmış bağlamdan daha çok yararlanabilir.
  - **Denenmemiş fikirler:**
    - Reranker + **3 chunk'lık bağlam** (minilm R@3 0,781 > baseline 0,719): Daha kısa prompt, daha hızlı ve daha az dikkat dağıtan bir cevap üretebilir.
    - bge'yi float16 ile çalıştırmak (gecikme).

### D34. Derlem 5 → 18 makale: aday seçimi, iki ingest düzeltmesi ve gerileme ölçümü
- **Neden önce derlem:** 5 makalede doğru chunk'ı bulmak kolaydı ve skorlar iyimser çıkıyordu. Ayrıca eval soruları yazıldıktan sonra makale eklenirse "dokümanda yok" soruları cevaplanabilir hâle gelebilirdi. Bu yüzden derlem, eval seti büyütülmeden önce büyütüldü.
- **Aday seçimi:**
  - Projenin kullandığı ya da kullanacağı tekniklerden 33 aday belirlendi; lisanslar arXiv OAI-PMH'tan kontrol edildi.
  - **13'ü CC BY 4.0:** ARES, ColBERTv2, Contriever, Multilingual E5, RAPTOR, GraphRAG, Chain-of-Thought, Self-Consistency, ReAct, Reflexion, Mistral 7B, vLLM, Docling.
  - Elenenler:
    - LoRA, DPR, HyDE, Lost in the Middle, Llama 2, MTEB ve diğerleri: arXiv varsayılan lisansı.
    - BEIR, Sentence-BERT: CC BY-SA.
    - SPLADE: CC BY-NC-SA.
  - Seçim ölçütü, eşleştirilebilir konular. Ragas ↔ ARES, E5 ↔ mE5 ↔ bge-m3 ↔ Contriever ↔ ColBERTv2, CoT ↔ Self-Consistency, ReAct ↔ Reflexion, RAPTOR ↔ GraphRAG çiftleri karşılaştırma soruları için doğal; aynı zamanda arama için gerçekçi dikkat dağıtıcılar.
  - Sürümler arXiv API'den alınıp sabitlendi (eval sayfa numaraları PDF sürümüne bağlı).
- **Sonuç:** 18 makale, 1734 chunk (metin 1103, tablo 412, şekil 219). Docling ile ayrıştırma 13 makalede 2 dk 25 sn; e5-small ile indeksleme 25 sn (Apple M4).
- **Düzeltme 1: yazar adları bölüm başlığı sanılıyordu.**
  - Docling, ilk sayfadaki yazar adlarını "section header" olarak etiketledi. ARES'te "Matei Zaharia" Giriş bölümünün ortasında başlık oldu ve sonraki 8 paragraf `§Matei Zaharia` diye kaynak gösterilecekti. Aynı durum Reflexion'da (5 yazar adı) ve Docling'de ("Version 1.0") da vardı.
  - Kural (`demote_front_matter_headings`): 1. sayfada numarasız bir başlık, yalnızca belgenin başlığıysa (ilk başlık), "Abstract" ya da "Introduction" ise bölüm başlangıcı sayılır; diğerleri düz metne çevrilir ve bölümler yeniden hesaplanır.
  - 8 başlık metne çevrildi (3 makale). Eski 5 makalede hiçbir eleman değişmedi. Docling'e bağlı olmayan saf bir fonksiyon olduğu için CI'da test ediliyor. `ingest.parse` çevrilen başlık sayısını yazdırıyor.
- **Düzeltme 2: uzun tablo altyazıları her parçada tekrarlanıyordu.**
  - Token sayacı (D24) 24 chunk'ın 512 sınırını aştığını yakaladı (en uzunu 787). Hepsi ARES tablolarından. Altyazılar bir paragraf uzunluğunda (Tablo 1'de 356 token); `split_table` altyazıyı ve başlık satırını her parçaya tekrar koyduğu için tek satırlık parçalar bile ~770 token'a çıkıyordu.
  - Kural: Altyazı bütçenin yarısını (200 token) aşıyorsa tam altyazı **bir kez** ayrı parça olarak indekslenir; satır parçalarına yalnızca başlığı konur ("Table 1: ARES Ranking ... GPT-3.5 Judge"). "vs." kısaltması yüzünden ilk noktadan değil, ikinci iki noktadan kesiliyor.
  - Eşik bilerek yüksek seçildi; yalnızca ARES'in 4 tablosu etkileniyor. Self-RAG Tablo 2 (145 token, bilinen "neredeyse kopya parçalar" sorunu) etkilenmiyor. Böylece eski 5 makalenin 469 chunk'ı **birebir aynı** kaldı (kontrol edildi) ve gerileme ölçümü yalnızca derlem büyümesini ölçüyor.
  - **Kalan 4 chunk kabul edildi:** ARES Tablo 6 çok geniş; sütun başlığı satırı tek başına 332 token, `|---|` ayırıcısı 90 token. Bu 4 chunk'ta (%0,2) indeksteki son ~35 token kesiliyor; LLM'e giden metin tam. Ayırıcıları bütün tablolarda sıkıştırmak bunu çözer, ama eski chunk'ları da değiştirir; ayrı bir ölçümle yapılmalı.
- **Gerileme ölçümü** (aynı 20 soru; `dense_tr_bm25_en`; e5-small; qwen3:4b-instruct; Apple M4):

| Varyant | R@1 | R@3 | R@5 | R@10 | MRR |
|---|---|---|---|---|---|
| dense | 0,375 → 0,375 | 0,531 → 0,469 | 0,594 → 0,469 | 0,750 → 0,750 | 0,509 → 0,481 |
| bm25_en | 0,469 → 0,594 | 0,656 → 0,719 | 0,750 → 0,750 | 0,906 → 0,750 | 0,646 → 0,693 |
| hybrid_en | 0,375 → 0,375 | 0,656 → 0,656 | 0,719 → 0,656 | 0,844 → 0,812 | 0,556 → 0,537 |
| **dense_tr_bm25_en** | 0,375 → 0,375 | 0,719 → 0,594 | 0,781 → 0,688 | 0,844 → 0,781 | 0,563 → 0,521 |

| Cevap eval | 5 makale | 18 makale |
|---|---|---|
| Doğru reddetme | 4/4 | 4/4 |
| Cevaplanan / kısmi / reddedilen (16) | 13 / 0 / 3 | 10 / 1 / 5 |
| Doğru (elle) | 10 | 9 |
| Gecikme (ortanca) | 8,2 sn | 7,3 sn |

- **Yorum:**
  - **Gerileme beklenen yönde ve büyüklükte:** Varsayılan varyantta R@5 −0,09 (16 soruda ~1,5 soru). 5 makalelik sonuçlar iyimsermiş; derlemi büyütmenin amacı bunu görmekti.
  - **Kardeş makale etkisi (q05):** mE5 de "query:/passage:" öneklerini anlatıyor. Onun chunk'ları E5'in 4. sayfasını bağlamdan itti; soru E5'i sorduğu için model doğru şekilde reddetti. Yeni eval soruları bu etkiyi bilinçli olarak ölçmeli (kardeş çiftler).
  - **"Yok" soruları hâlâ geçerli:** q19'da bağlama mE5 chunk'ları, q18'de Mistral'in lisans chunk'ı girdi; model ikisinde de doğru şekilde reddetti.
  - **bm25_en'nin R@1'i arttı** (0,469 → 0,594). Olası açıklama, idf'in derleme bağlı olması: kelimelerin ayırt ediciliği değişti. Bu bir tahmin, ölçülmedi.
  - **Varyant kararı (D32) değişmedi:** 16 soruda farklar hâlâ birkaç soruluk; yeniden karar 40–60 soruluk eval setiyle verilecek.

### D35. Eval sorularının doğrulanması: elle değil, kanıtla
- **Durum:** İlk 20 soru elle, PDF'e bakılarak doğrulandı. Set 40–60 soruya büyürken kalan soruları elle kontrol etmek istemedim. Ama taslakları Claude yazıyor; hiç kontrol edilmezse eval, onun hatalarını "doğru cevap" diye kabul eder. Sistem doğru cevap verse bile yanlış sayılabilir.
- **Değerlendirilen seçenekler:**
  1. **Otomatik kanıt kontrolü.** Seçildi.
  2. Kanıt kontrolü + her partide rastgele 1 sorunun elle kontrolü (örnekleme).
  3. İkinci bir LLM'e kontrol ettirmek. Elendi: yerelde çalışabilecek modeller taslağı yazandan daha güvenilir bir hakem değil; ayrıca RAGAS hakemiyle iç içe geçer.
- **Nasıl çalışıyor:**
  - Elle doğrulanmamış (`verified: false`) her cevaplanabilir soru, **her kaynak sayfası için** o sayfanın ayrıştırılmış metninden birebir kopyalanmış bir alıntı taşır (`evidence`: paper, page, quote; en az 20 karakter).
  - "Dokümanda yok" soruları, adı geçen belgede **hiç geçmemesi gereken** kelimeleri taşır (`absent_terms`).
  - Şema bunu yükleme sırasında zorunlu kılıyor: Kanıtı olmayan doğrulanmamış bir soru yüklenemez, sessizce eval'e giremez.
  - `eval/check_evidence.py` alıntıları sayfalarda, yok kelimelerini belgelerde arar. Büyük/küçük harf ve boşluk farkı yok sayılır; "İ" önce "i"ye çevrilir (Python'un `lower()` sorunu, D29).
- **Neden Docling'in metniyle karşılaştırılıyor:** Alıntılar PDF'in kendisiyle değil, sistemin gördüğü ayrıştırılmış metinle karşılaştırılıyor. Docling'in yanlış okuduğu bir kelime alıntıda da aynı yanlışla geçer; eval sistemin gerçekte erişebildiği bilgiyi ölçmeli.
- **Kontrolün kendisi test edildi:** Gerçek veride q21'in sayfası bilerek 2'den 3'e çevrildiğinde eksik alıntı raporlandı; q30'a makalede geçen bir kelime ("sliding window") eklendiğinde de yakalandı. Hiç başarısız olmayan bir kontrol, çalıştığını kanıtlamaz.
- **Yakaladıkları:** Yanlış sayfa, yanlış belge, uydurulmuş ya da yanlış hatırlanmış alıntı, aslında cevaplanabilir olan "yok" sorusu.
- **Yakalayamadıkları:**
  - Doğru bir alıntıdan yanlış bir cevap çıkarılması (ör. q24 ve q25'teki çıkarma işlemleri).
  - Belirsiz yazılmış sorular.
  - Bu, elle doğrulamaya göre daha zayıf bir güvence; sonuç dosyalarına yazılıyor (`verified_by_human`, `verified_by_evidence`).
- **Sınır:** Kontrol `data/parsed/` gerektirdiği için CI'da çalışmıyor (PDF'ler git'te yok, D9). CI yalnızca şemayı, yani kanıtın var olduğunu doğruluyor; alıntıların sayfalarda gerçekten geçtiğini yerel kontrol doğruluyor.
- **Çeviriler:** Yeni soruların çevirileri elle kontrol edilmedi (`reviewed: false`). Ölçüm zaten ham çeviriyle yapılıyor (D32). Bilinen iki çeviri hatası:
  - q26: "ilk şekil" çevrilmemiş.
  - q30: cümle anlam olarak bozuk.
  - q32: karşılaştırmanın yönü ters çevrilmiş (pypdfium ↔ Docling'in kendi arka ucu).
  - q37: "yer kaplama" (space footprint) yerine "poor coverage" yazılmış.
  - **q42: çeviri yerine uydurma.** Model soruyu çevirmedi; olmayan bir cevap yazdı: "ARES evaluates a RAG system by measuring three things: Recall@100, Precision@100, and Retrieval Quality." Dense kol Türkçe soruyla çalıştığı için doğru sayfa yine 2. sırada geldi (D32'deki "Türkçe kol sigorta" gerekçesi), ama BM25'e makalede olmayan terimler gitti. Guardrail adayı (G2): Çeviri soru biçiminde mi, uzunluğu orijinale yakın mı?
- **Son durum (7b):** 49 soru.
  - Türlere göre: 15 tek sayfa, 10 tablo, 8 şekil, 8 karşılaştırma, 8 yok.
  - İfade biçimine göre: 22 term, 15 paraphrase, 12 inference.
  - Doğrulama: 20'si elle, 29'u kanıtla; kanıt kontrolü 0 hata.
  - Hızlı eval (`dense_tr_bm25_en`, e5-small, 18 makale, 41 cevaplanabilir soru):

    | | n | R@5 | MRR |
    |---|---|---|---|
    | Tümü | 41 | 0,671 | 0,491 |
    | `term` | 16 | 0,750 | 0,524 |
    | `paraphrase` | 14 | 0,607 | 0,375 |
    | `inference` | 11 | 0,636 | 0,591 |
    | Şekil | 8 | 0,500 | 0,192 (R@1 = 0) |
    | Tablo | 10 | 1,000 | 0,853 |
    | Karşılaştırma | 8 | 0,438 | 0,455 |
- **Etiket düzeltmesi:** `eval.check_phrasing` q34 için "value, vectors" uyarısı verdi. Haklıydı: "anahtar ve değer vektörleri" makalenin kendi terimi; etiket `paraphrase`'den `term`'e çevrildi. Sıradan kelimelerden kaynaklanan uyarılar (q21 "store", q22 "limit", q37 "vectors", q38 "stage") bilerek bırakıldı. Eşik, uyarı çıkmasın diye ayarlanmadı.

### D36. 49 soruluk cevap eval'i (baseline): tablolarda iki farklı hata
- **Kurulum:** `dense_tr_bm25_en`, e5-small, 18 makale, reranker yok, qwen3:4b-instruct, bağlamda 5 chunk, Apple M4.
- **Otomatik sayımlar:**
  - Doğru reddetme: **8/8**. Tuzak sorular dahil: q30 Mistral'in eğitim verisi, q40 Self-Consistency'de GPT-4, q48 vLLM'in Apple'da çalışması, q49 GraphRAG'in RAPTOR'la karşılaştırılması.
  - 41 cevaplanabilir sorudan: 30 cevap, 2 kısmi, 9 ret.
  - Gecikme (ortanca): 8,5 sn.
  - "Uydurma etiket" uyarısı 2 soruda (q26, q47); q47'de yalnızca bölüm numarası farklı (§4.2 yerine §4).
- **Tekrarlanabilirlik:** q01–q20'nin 20 cevabı, aynı derlemdeki önceki koşuyla birebir aynı.
- **Doğruluk** (elle, beklenen cevapla karşılaştırarak, tek koşu): **24/41** (%59).
  - Eski 16 soru: 9 doğru.
  - Yeni 25 soru: 15 doğru.
    - Doğru: q22, q23, q24, q27, q28, q29, q34, q35, q36, q37, q38, q41, q42, q43, q47.
    - Yanlış ya da reddedilen: q21, q25, q26, q31, q32, q33, q39, q44, q45, q46.
  - Kardeş makale testleri geçti: q38'de mE5'in 1 milyar çifti doğru, E5'in CCPairs'i ile karışmadı; q42'de ARES'in üç ölçütü doğru, Ragas ile karışmadı.
- **Türlere göre doğru cevap:**

| Tür | Doğru | Arama R@5 |
|---|---|---|
| Tablo | **2/10** | **1,000** |
| Şekil | 6/8 | 0,500 |

  - Tablolarda arama "her şeyi buluyor" ama cevaplar en kötü. Şekillerde arama en zayıf ama cevaplar iyi: Şekli anlatan metin paragrafları çoğu zaman yetiyor (q27, q35).
- **Tablo hatalarının iki nedeni** (6 yeni tablo sorusu, kanıt alıntılarının bağlamda olup olmadığına bakılarak):
  - **A) Chunk düzeyinde arama (3 soru: q25, q31, q44).** Doğru sayfa bağlamda, ama gereken satırlar yok. Tablo satır gruplarına bölünüyor; q25'te Mistral'in satırı bağlamda, karşılaştırılacak Llama 2 13B satırı başka bir parçada kalmış. Sayfa düzeyindeki Recall bunu isabet sayıyor; D28'deki "doğru sayfa ≠ doğru chunk" uyarısının ölçülmüş hâli.
  - **B) LLM'in tablo okuması (3 soru: q32, q33, q45).** Gereken satırlar bağlamda, ama model reddediyor (q32, q45) ya da yanlış satırı okuyor (q33: BM25 satırı yerine SBERT satırı).
- **Sonuçlar:**
  1. **Kanıt alıntıları chunk düzeyinde bir ölçüt sağlıyor.** Elle doğrulanmamış her soruda, cevabı içeren cümleler biliniyor. "Getirilen chunk'lar kanıt alıntılarının ne kadarını içeriyor?" (evidence recall) LLM'siz, hızlı eval'e eklenebilir. Bu, D28'den beri açık olan "chunk düzeyinde ölçüt" sorusunun cevabı.
  2. **A için çözüm adayları:** Tablo parçalarına başlık satırı zaten tekrarlanıyor. Bir parça gelince aynı tablonun komşu parçalarını da bağlama eklemek ("parent document" fikri) ya da küçük tabloları hiç bölmemek denenebilir.
  3. **B için çözüm adayları:** Daha büyük model (Aşama 9) ya da tabloyu satır satır "anahtar: değer" metnine çevirmek. Ayrıca G1'deki tablo okuma aracı.
  4. Hepsi ölçülerek denenmeli; önce ölçüt (1).

### D37. Chunk düzeyinde ölçüt (evidence recall) ve hızlı eval ile cevap zinciri arasındaki fark
- **Ölçüt:** Kanıt alıntısı olan 25 cevaplanabilir soruda iki ölçüt:
  - `evidence_recall@k`: Sorunun kanıt alıntılarından kaçı ilk k chunk'ın metninde geçiyor?
  - `evidence_complete@k`: Hepsi birlikte geçiyor mu?
  - İkincisi karşılaştırma ve iki satırlık tablo soruları için gerekli; tek parça cevap için yetmez.
  - LLM'siz; hızlı eval'e eklendi. Cevap eval'inde her soruya `evidence_in_context` yazılıyor.
- **Ölçütün güvenilirliği:** Bir alıntı iki chunk'a bölünmüşse hiçbir zaman bulunamaz. `eval.check_evidence` bunu sayıyor: 0 alıntı bölünmüş.
- **Sonuç** (`dense_tr_bm25_en`, e5-small, 18 makale, k=5):

| | Sayfa R@5 (41 soru) | Evidence recall@5 (25) | Evidence complete@5 |
|---|---|---|---|
| Tümü | 0,671 | 0,540 | 0,400 |
| Tek sayfa | 0,667 | 0,389 | 0,333 |
| Tablo | 1,000 | 0,917 | 0,833 |
| Şekil | 0,500 | 0,400 | 0,400 |
| Karşılaştırma | 0,438 | 0,500 | **0,000** |

  - İki ölçüt farklı soru kümelerinde hesaplanıyor; doğrudan karşılaştırma yaklaşık.
  - Tek sayfa sorularında doğru sayfa %67, cevabı içeren cümle %39 geliyor.
  - Karşılaştırma sorularının hiçbirinde iki makalenin kanıtı birlikte ilk 5'e girmiyor (çeşitlilik sorunu, D33).
- **Varyant karşılaştırması** (evidence recall@5 / complete@5):

| Varyant | Recall@5 | Complete@5 | Not |
|---|---|---|---|
| `dense_tr_bm25_en` | 0,540 | 0,400 | |
| `dense` | 0,407 | 0,240 | Şekillerde 0 |
| `bm25_en` | 0,353 | 0,280 | |

  - Hibritin üstünlüğü chunk düzeyinde de geçerli.
- **Bulunan ölçüm tutarsızlığı:**
  - Hızlı eval retriever'ı k=10 ile kuruyor (her kol 10 sonuç, RRF, sonra ilk 5'e bakılıyor). Cevap zinciri ise k=5 ile (her kol 5 sonuç).
  - RRF puanı bir chunk'ın diğer listede de olup olmamasına bağlı; bu yüzden iki kurulumun "ilk 5"i farklı.
  - Örnek: q31'in ve q44'ün gereken satırları hızlı eval'de ilk 5'te (1/1, 3/3), cevap eval'inde LLM'in bağlamında yoktu (D36).
  - Yani şimdiye kadarki R@5 değerleri, LLM'e giden 5 chunk'ı tam olarak ölçmüyordu. (Tek motorlu varyantlarda fark yok; ilk 5 aynı.)
- **Önerilen düzeltme (ölçülecek):** Kol derinliğini k'dan ayırmak (ör. her kol 20 sonuç, birleştirmeden sonra k). Hızlı eval ile cevap zinciri aynı derinliği kullanır, ölçülen ile LLM'in gördüğü aynı olur. Derin listelerde RRF'nin uzlaşma sinyali de daha güçlü.

### D38. Kol derinliği 20: LLM'e giden kanıt arttı, doğru cevap sayısı değişmedi
- **Değişiklik:** `RETRIEVAL_DEPTH` (varsayılan 20). Her kol 20 sonuç getiriyor, RRF birleştiriyor, sonuç k'ya kesiliyor. Reranker açıkken derinlik en az aday sayısı kadar.
  - Tek kollu varyantlarda sonuç değişmiyor.
  - Çok kollu varyantların sonuç dosyası adında `_depth20` var.
- **Neden:** Hızlı eval (k=10) ile cevap zinciri (k=5) farklı "ilk 5" görüyordu (D37). Artık ikisi de aynı derinliği kullanıyor; hızlı eval LLM'in gördüğü bağlamı ölçüyor.
- **Açıklamanın doğrulanması:** Cevap zincirinin eski kurulumu (k=5, derinlik 5) yeniden çalıştırıldı. q31 ve q44'ün satırları bağlamda yok; D36'daki cevap eval'iyle birebir aynı.
- **Hızlı eval** (`dense_tr_bm25_en`, k=10, 41 cevaplanabilir / 25 kanıtlı soru):

| Derinlik | Sayfa R@5 | R@10 | MRR | Evidence recall@5 | Evidence complete@5 |
|---|---|---|---|---|---|
| 10 | 0,671 | 0,768 | 0,491 | 0,540 | 0,400 |
| **20** | 0,768 | 0,866 | 0,509 | **0,587** | **0,440** |
| 50 | 0,780 | 0,878 | 0,520 | 0,533 | 0,360 |

  - Derinlik 20 ölçümden önce seçilmişti. 50 sayfa düzeyinde biraz daha iyi, ama chunk düzeyinde kötü: daha derin listeler daha çok gürültü de getiriyor.
  - Hızlı eval k=10 kullandığı için "derinlik 5" ölçülemedi (`max(depth, k)`); bu karşılaştırma doğrudan cevap zinciriyle yapıldı.
- **Cevap eval** (qwen3:4b-instruct, bağlamda 5 chunk, Apple M4):

| | Derinlik 5 (D36) | Derinlik 20 |
|---|---|---|
| LLM bağlamında kanıt: recall / complete | 0,447 / 0,280 | **0,587 / 0,440** |
| Doğru reddetme | 8/8 | 8/8 |
| Doğru cevap (elle) | 24/41 | **24/41** |
| Gecikme (ortanca) | 8,5 sn | 10,1 sn |

  - Değişen sorular:
    - Kazanılan: q02, q46.
    - Kaybedilen: q11, q13 (reddediyor; q13'te kaynak bağlamdan düştü).
  - 49 cevabın 29'u değişti; 20'si aynı.
  - Gecikme artışının nedeni ölçülmedi (bağlam yine 5 chunk).
- **Sonuç: darboğaz artık LLM'in okuması.**
  - q44: Gereken 3 satırın üçü de bağlamda, model yine "ReAct daha iyi" diyor (27,4 < 29,4).
  - q33: İki satır da bağlamda, model yine SBERT satırını okuyor.
  - Arama tarafındaki iyileştirmeler 4B modelle cevaba yansımıyor. Daha büyük model (Aşama 9) ya da tabloları satır satır metne çevirmek (D36) ölçülecek.
- **Karar:** Derinlik 20 kalıyor. Gerekçeler:
  1. Ölçüm doğruluğu: hızlı eval ile LLM'in bağlamı aynı.
  2. Chunk düzeyinde gerçek kazanç.
  3. Cevaplarda kayıp yok.
- **Yan gözlem:** q01'in cevabında Çince bir kelime var ("检索" = retrieval). Qwen modeli zaman zaman Çince token sızdırıyor.

### D39. Tam eval: RAGAS + yerel hakem (gemma3:12b); faithfulness doğruluk değildir
- **Hakem seçimi:** `gemma3:12b` (Ollama, 4-bit, 8,2 GB), temperature 0.
  - Gerekçeler:
    - Bilgisayarın 16 GB belleğine sığıyor.
    - Çok dilli: Türkçe cevapları İngilizce bağlamla karşılaştırabiliyor.
    - Cevap modelinden (Qwen) farklı aileden: LLM hakemlerin kendi ailesinin çıktısını kayırma eğilimi (self-preference bias) var.
    - "Thinking" modu yok (D27).
  - Elenenler: qwen2.5:14b (aynı aile), phi4 (ağırlıkla İngilizce), mistral-nemo.
  - Adaylar ve boyutlar Ollama model sayfalarından kontrol edildi.
- **RAGAS paketi:** 0.4.4, ayrı bir `eval` bağımlılık grubunda (CI ve uygulama kurmuyor). Tam eval `uv run --group eval python -m eval.full <cevap dosyası>`.
  - **Bağımlılık bedeli 1:** RAGAS `langchain-community`'ye bağımlı. Bizim kodumuz onu import etmiyor; uygulama imajına girmiyor (D29'daki kural yalnızca bizim kodumuz için).
  - **Bağımlılık bedeli 2:** RAGAS'ın kullandığı instructor (`jiter<0.15`) yüzünden `openai` paketi 3.58'den 3.3'e indi. uv tek bir kilit dosyası tuttuğu için bu uygulamayı da etkiliyor. Testler, doğrudan LLM çağrısı ve uçtan uca soru sorunsuz. İleride `langchain-openai` daha yeni bir `openai` isterse çakışabilir.
  - **Bakım:** 0.4.3 ile 0.4.4 arasında 10 ay var.
- **RAGAS içeride ne yapıyor** (`ragas/metrics/collections`, kaynak kodundan):
  - **Faithfulness:**
    1. Hakem cevabı atomik iddialara bölüyor.
    2. Hakem her iddia için bağlamdan çıkarılabilir mi diye karar veriyor (NLI).
    3. Puan = desteklenen iddia / tüm iddialar. İddia yoksa (ret cevabı) `NaN`; retler bu yüzden puanlanmıyor, kendi metriğimizle ölçülüyor (8/8).
  - **Answer relevancy:**
    1. Hakem cevaba bakıp "bu cevap hangi soruya verilmiş?" sorusunu yazıyor ve kaçamak (noncommittal) cevapları işaretliyor.
    2. Puan = üretilen soru ile gerçek soru arasındaki kosinüs benzerliği (e5, `query:` önekiyle); kaçamak cevapta 0.
    3. RAGAS bunu `strictness` kez aynı prompt'la soruyor; temperature 0'da sorular aynı çıkacağı için `strictness=1`.
- **Bulunan hata: kaynak etiketi cezası.**
  - İlk denemede hakeme chunk'ların düz metni verildi. Hakem, cevaptaki `[bge_m3, s.7, §4.2]` etiketini ayrı bir iddia olarak çıkardı ve bağlamda bulamadığı için "desteklenmiyor" dedi. Doğru bir cevap (q03) 0,67 aldı.
  - Kaynak gösteren her cevap haksız yere ceza alıyordu; yani projenin temel özelliği puanı düşürüyordu.
  - **Düzeltme:** Hakeme bağlam, cevap modelinin gördüğü biçimde (`format_docs`: etiket + metin) veriliyor. q02 ve q03 1,0'a çıktı; answer relevancy değişmedi (bağlam kullanmıyor). Testle sabitlendi.
- **Sonuç** (derinlik 20 cevapları, D38; 30 cevap; 0 puanlanamayan; soru başına 97–270 sn, toplam ~1,5 saat, MacBook Air M4):

| | Faithfulness | Answer relevancy |
|---|---|---|
| Tümü (30) | **0,910** | **0,877** |
| Elle "doğru" (24) | 0,944 | 0,881 |
| Elle "yanlış" (6) | 0,770 | 0,860 |

- **RAGAS ile elle doğruluk karşılaştırması:**
  - Faithfulness < 1 olan 7 cevaptan 3'ü gerçekten yanlış (q21, q39, q44); 4'ü doğru (q22, q24, q35, q43).
  - Yanlış cevaplardan 3'ü faithfulness 1,0 aldı (q14, q26, q33).
  - **Hakemin doğru yakaladığı örnek (q44):** "ReAct, CoT'den daha iyi" iddiası reddedildi, gerekçe doğru: "27,4 EM < 29,4 EM". Tabloyu 4B cevap modeli yanlış okudu, 12B hakem doğru okudu.
  - **Hakemin yanıldığı örnek (q22):** "W = 4096 token" iddiası bağlamda açıkça yazıyor; hakem aynı paragraftaki 131K ve 16K sayılarına takılıp reddetti.
  - **Faithfulness'ın tanım gereği kaçırdıkları:**
    - q33: Model yanlış satırı okudu (BM25 yerine SBERT), ama yazdığı sayılar bağlamda var: "sadık ama yanlış".
    - q14, q26: Bağlamdaki doğru ama soruyu cevaplamayan bilgiler.
  - **Answer relevancy bu sette ayırt edici değil:** Tüm cevaplar 0,79–0,92 aralığında; yanlışlar da soruyla "ilgili".
- **Sonuçlar (mülakat notu):**
  1. **Faithfulness doğruluğu değil, sadakati ölçer.** "Bağlamda olmayan bir şey söyledi mi?" sorusunu cevaplar; "doğru soruyu doğru cevapladı mı?" sorusunu cevaplamaz. Uydurmayı yakalamak için iyi, yanlış okumayı ya da yanlış satır seçmeyi yakalamak için değil.
  2. **Hakem de hata yapar** (q22). Puanlar bir ölçüm aracıdır, gerçek değildir. Hakemin kendisi de örnekleme ile kontrol edilmeli.
  3. **Doğruluk için referans gerekir:** Beklenen cevaplar elimizde. RAGAS'ın referanslı ölçütleri (ör. answer correctness / factual correctness) ya da beklenen cevapla karşılaştıran bir hakem prompt'u bir sonraki adım olabilir; aynı hakemle ölçülmeli.
- **Süre:** 30 cevap ~1,5 saat. Bu yüzden tam eval CI'da değil, birleştirmeden önce yerelde çalışıyor (CLAUDE.md'deki iki katmanlı eval).

### D40. Referanslı doğruluk: RAGAS AnswerAccuracy, elle etiketlerle %90 uyum
- **Neden:** Faithfulness doğruluğu ölçmüyor; "sadık ama yanlış" cevaplara tam puan veriyor (D39, q33). Beklenen cevaplar elimizde olduğu için cevabı doğrudan onlarla karşılaştıran bir ölçüt eklendi.
- **Değerlendirilen RAGAS ölçütleri** (kaynak kodundan):
  - **AnswerAccuracy** (NVIDIA'nın çift hakem yaklaşımı): Hakem cevabı referansla karşılaştırıp 0 (uyuşmuyor), 2 (kısmen) ya da 4 (tam) diyor. İkinci bir prompt aynı işi cevap ile referansın yerleri değiştirilmiş olarak yapıyor. Puan = iki puanın ortalaması / 4. 0,25 ve 0,75, iki hakemin farklı karar verdiği durumlar. Soru başına 2 kısa çağrı. **Seçildi.**
  - FactualCorrectness: Cevap ve referans iddialara bölünüp iki yönde karşılaştırılıyor. Elendi: beklenen cevaplarımız ayrıntılı, kısa ama doğru cevaplar recall yönünde haksız ceza alır.
  - AnswerCorrectness: İddia düzeyinde F1 + embedding benzerliği. Elendi: benzerlik "konudan bahsetmeyi" ödüllendirir, q33 tipi hataları gizler.
- **Tasarım:**
  - Bütün cevaplanabilir sorular (41) puanlanıyor. Ret cevabı yanlış bir cevaptır; LLM'e sorulmadan 0 alıyor.
  - "Dokümanda yok" soruları burada değil, ret oranıyla ölçülüyor.
  - RAGAS, bozuk JSON'da yeniden deneyip sessizce `NaN` döndürüyor; bizim kodumuz `NaN`'ı sayıyor (bu koşuda 0).
  - `--metrics answer_accuracy` ile yalnızca bu ölçüt çalışıyor: 41 soru 9 dakika (faithfulness ile birlikte ~1,5 saat).
- **Sonuç** (derinlik 20 cevapları, gemma3:12b, Apple M4):
  - Ortalama 0,433.
  - Puan dağılımı: 0 → 11 soru, 0,25 → 4, 0,5 → 14, 0,75 → 9, 1,0 → 3.

| "Doğru" eşiği | Hakeme göre doğru | Elle etiketlerle uyum |
|---|---|---|
| **≥ 0,5** (kısmen ya da tam) | 26 (elle: 24) | **37/41 (%90)** |
| = 1,0 (tam) | 3 | 20/41 |

- **Faithfulness'ın kaçırdıklarını yakalıyor:** q33 (yanlış tablo satırı) 0,25, q26 0,25, q21 0,25. Faithfulness q33 ve q26'ya 1,0 vermişti.
- **Ayrışmalar (≥ 0,5 eşiğinde, 4 soru):**
  - q44, q39, q14: Hakem 0,5 verdi, elle "yanlış" saymıştım. Üçü de yarı doğru: q44'te en iyi yöntem doğru, "ReAct daha mı iyi?" yanlış; q39'da E5 kısmı doğru, Contriever kısmı eksik. Elle değerlendirmede karşılaştırma ve evet/hayır sorularında daha katı davranmışım.
  - q23: Elle doğru, hakem < 0,5. Cevap doğru sonuca varıyor ama beklenen cevaptaki "~100B parametre" bilgisini atlıyor.
- **Eşik seçimi:** Sonuçlara bakıldıktan sonra seçildi. Ama yalnızca iki doğal seçenek karşılaştırıldı ("kısmen veya daha iyi" ve "tam"); uyumu artırmak için ara değerler denenmedi.
  - "= 1,0" kullanışsız: NVIDIA prompt'u "bütün sayılar ve terimler eşdeğer" diyor; ayrıntılı referanslarımız yüzünden doğru cevapların çoğu 0,5–0,75 alıyor.
- **Türlere göre ortalama:**

| Tür | Ortalama |
|---|---|
| Tek sayfa | 0,600 |
| Karşılaştırma | 0,500 |
| Şekil | 0,281 |
| Tablo | **0,250** |

  - Tablo zayıflığı (D36, D38) otomatik ölçümde de görülüyor.
- **Karar:** Tam eval'in ana doğruluk ölçütü "answer accuracy ≥ 0,5 oranı" (bu koşuda 26/41). Ortalama ile birlikte raporlanacak. Elle sayım artık yalnızca hakemi örnekleme ile kontrol etmek için yapılacak.
- **Sınırlar:**
  - Tek koşu, tek hakem.
  - Referansları cevap modeliyle aynı bilgiden ben (Claude) yazdım. 20'si elle, 29'u kanıtla doğrulandı (D35).
  - %90 uyum 41 soruya dayanıyor; ayrışan 4 sorunun hepsi "yarı doğru" türünden.

### D41. Langfuse: yerelde Docker ile (self-host v4), LangChain callback'i
- **Karar:** Langfuse yerelde, `infra/docker-compose.obs.yml` (profil `obs`).
  - Gerekçeler: Ücretsiz; izler (sorular, getirilen parçalar) bilgisayardan çıkmıyor. Kişisel belgelerle çalışılırsa önemli.
  - Alternatif: Langfuse Cloud ücretsiz katmanı. Kurulum yok, ama veri dışarı gidiyor.
- **Kaynaktan doğrulananlar** (tahmin edilmedi):
  - Sunucu artık **v4**. Resmî compose dosyası (langfuse/langfuse `main`) okundu; imajlar en son sürüme, **4.88.0**'a sabitlendi (neredeyse her gün sürüm çıkıyor).
  - Python SDK **5.2.0**. İzleri OpenTelemetry ile gönderiyor; bağımlılıkları hafif (`langchain-community` yok). Ekleyince hiçbir paketin sürümü düşmedi.
- **Resmî dosyadan farklar:**
  - AI gateway yok. LLM çağrılarını Langfuse üzerinden yönlendiren isteğe bağlı bir proxy; hiçbir servis ona bağımlı değil.
  - `TELEMETRY_ENABLED=false`: Langfuse'a kullanım istatistiği gitmiyor.
  - Bilgisayara açılan tek port web arayüzü (3000), o da yalnızca `127.0.0.1`'e. Resmî dosyada 3000 ve MinIO'nun portu bütün ağ arayüzlerine açıktı. Diğer servisler yalnızca Docker'ın iç ağında.
  - ~100 ortam değişkeninden yalnızca gerekenler alındı.
  - İlk açılışta organizasyon, proje, API anahtarları ve giriş kullanıcısı `LANGFUSE_INIT_*` ile otomatik oluşturuluyor; arayüzde kayıt gerekmiyor. Giriş e-postası yerel bir ad (`admin@example.com`); gerçek adres kullanılmadı.
- **Ayrı compose dosyası neden:** Parolalar `${VAR:?...}` ile zorunlu; eksikse açık bir hata veriliyor. Ama compose bu kontrolü profili kapalı servisler dahil dosyanın tamamında yapıyor. Ana dosyada olsaydı, `infra/.env` olmayan bir makinede (ör. yeni bir klon) `docker compose up -d qdrant` da hata verirdi. Bu test edilerek görüldü.
- **Parolalar:** `infra/make_secrets.py`, `secrets` modülüyle (kriptografik rastgelelik) üretip `infra/.env` dosyasına yazıyor (izin 600, git'e girmiyor).
  - Dosya varsa üzerine yazmıyor: veritabanları ilk parolalarıyla kuruldu, yeni parolalar Langfuse'u kendi verisinden kilitler.
  - Uygulamanın 3 ayarını (`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`) ana `.env`'ye ekliyor.
  - Hiçbir parolayı ekrana yazdırmıyor.
- **Uygulama tarafı (`app/tracing.py`):**
  - LangChain her adımın başında ve sonunda callback'leri çağırıyor. Langfuse'un `CallbackHandler`'ı bu olaylardan soru başına iç içe bir iz ağacı kuruyor: girdiler, çıktılar, süreler, token sayıları.
  - **Tuzak:** `pydantic-settings` `.env`'yi okuyor ama ortam değişkenlerine yazmıyor; SDK ise yalnızca ortam değişkenlerine bakıyor. Bu yüzden istemci ayarlardan açıkça oluşturuluyor (`Langfuse(public_key=..., secret_key=..., base_url=...)`). Handler istemciyi public key ile buluyor (singleton, SDK kaynağından).
  - Anahtar yoksa hiçbir şey import edilmiyor ve gönderilmiyor; testle sabitlendi.
  - İzlerde etiketler var (retriever, model). Bir cevap eval koşusunun bütün soruları tek bir oturumda (`langfuse_session_id`) toplanıyor.
  - Zincirin adımlarına `run_name` verildi: `query`, `translate`, `retrieve`, `format_context`, `generate`. İzlerde `RunnableSequence` gibi genel adlar yerine bunlar görünüyor.
- **İzin geldiği doğrulandı (API ile, arayüze bakmadan):**
  - v4'te eski `GET /api/public/traces` kaldırılmış ("events_only mode"). Gerçek zamanlı okuma `GET /api/public/v2/observations` ile; sunucunun OpenAPI dosyasından bulundu.
  - Bir soru = 32 gözlem.
  - İlk koşu (soğuk): toplam 8,70 sn = çeviri 3,68 + arama 0,22 (dense 0,216, BM25 0,003) + cevap 4,79.
  - Aynı soru ikinci kez: toplam 2,03 sn = çeviri 0,54 + arama 0,04 + cevap 1,46.
  - İlk koşuda Ollama modeli soğuk yüklüyordu. Aynı soru olduğu için Ollama'nın prompt önbelleği de etkili olabilir; iki etki ayrıştırılmadı.
- **Kaynak ölçümü** (`docker stats`, Apple M4, Docker'a 8 GB ayrılmış):
  - Langfuse ~3,1 GB bellek: web 1,2 GB, worker 0,9 GB, ClickHouse 0,9 GB, diğerleri < 0,1 GB.
  - İmajlar ~4 GB disk.
  - Hakem modeliyle (gemma3:12b, ~8 GB, Docker dışında Ollama) aynı anda çalışınca 16 GB zorlanabilir: tam eval sırasında Langfuse kapatılmalı.
- **Güvenlik notu:** Giriş parolası ve API anahtarları yalnızca yerel `.env` dosyalarında. Arayüz yalnızca bu bilgisayardan erişilebilir.

### D42. CI'da hızlı eval: chunk dosyası GitHub Release'te, Qdrant bellekte
- **Sorun:** Hızlı eval chunk'lara (BM25 ve vektörler için) ve Qdrant'taki indekse ihtiyaç duyuyor. PDF'ler, chunk'lar ve indeks git'te değil (CLAUDE.md); CI'da Qdrant sunucusu da yok.
- **Değerlendirilen seçenekler:**
  - A) Sıkıştırılmış chunk dosyasını (0,4 MB) git'e koymak.
  - **B) GitHub Release eki (asset) olarak yayımlamak. Seçildi (kullanıcı kararı):** Türetilmiş veri repoda değil, release'te duruyor; "indeks verisi git'e girmez" kuralı değişmiyor.
  - C) CI'ın PDF'leri arXiv'den indirip Docling ile ayrıştırması. Elendi: yavaş (Docling M4'te bile 2,5 dk); arXiv'e her push'ta yük biniyor; arXiv erişilemezse CI kırılıyor.
- **Lisans (CC BY 4.0, hukuki metin okundu):**
  - Madde 2(a)(1): Materyalin tamamen ya da kısmen paylaşılmasına ve uyarlanmış materyal paylaşılmasına izin veriyor.
  - Madde 3(a)(1): Paylaşan kişi yazarları, (varsa) telif bildirimini, lisans bağlantısını, materyalin bağlantısını ve **yapılan değişiklikleri** belirtmeli.
  - Madde 3(a)(2): Bu bilgiler, onları içeren bir kaynağa bağlantı vererek de sağlanabilir.
  - Release'e yükleme de "paylaşma" sayılıyor; şartlar B için de geçerli.
  - `data/SOURCES.md`'de yazarlar, lisans bağlantısı ve değişiklik listesi **eksikti**. Eksiklik ham PDF'lerin indirilmesi için de vardı; bu iş sırasında görüldü ve "Attribution" bölümü eklendi.
    - Yazarlar arXiv API'sinden alındı.
    - Telif bildirimleri ayrıştırılmış metinde arandı. vLLM'de "© 2023 Copyright held by the owner/author(s)" (ACM, SOSP '23) var. Docling'deki ACM metni, örnek olarak gösterilen başka bir makalenin (DocLayNet) sayfasına ait.
  - Release'e `NOTICE.md` ekleniyor: lisans bağlantısı, yazarlar, değişiklikler.
- **Nasıl çalışıyor (`eval/ci_data.py`):**
  - `build` (yerelde):
    - `data/chunks.jsonl`'ü deterministik olarak sıkıştırıyor (`mtime=0`: aynı içerik, aynı `.gz`).
    - Etiketi içeriğin SHA-256 özetinden türetiyor (`ci-data-93c3e5c62725`) ve `eval/ci_data.json`'a yazıyor (etiket, özet, 1734 chunk, 18 makale).
    - Kullanıcının çalıştıracağı `gh release create` komutunu veriyor.
    - Her chunk sürümünün kendi release'i var; eskiler silinmiyor.
  - `verify` (CI): İndirilen dosyanın özeti kayıtla uyuşmazsa CI duruyor.
  - **Bayatlık koruması:** Bir test, yereldeki `data/chunks.jsonl` ile kayıtlı özeti karşılaştırıyor. Chunking değişip yeni release yayımlanmazsa yerelde kırılıyor; CI eski chunk'larla ölçmüyor.
- **Bellekte Qdrant:** `QDRANT_URL=:memory:` olunca `get_vectorstore` sunucuya bağlanmak yerine chunk'ları işlem başına bir kez vektöre çevirip bellekte indeksliyor.
  - Aynı ayar `app.ask` için de çalışıyor.
  - Sonuçlar sunucuyla birebir aynı (R@5 0,768, MRR 0,509, evidence recall@5 0,587). M4'te 1734 chunk 25 sn'de vektöre çevriliyor.
- **CI işi (`fast-eval`):**
  1. Chunk dosyasını indir ve özetini doğrula.
  2. e5-small'ı önbellekten al (`actions/cache`).
  3. Hızlı eval'i çalıştır.
  4. Sonuç dosyasını ve logu artifact olarak sakla.
  - Birim testlerinden ayrı bir iş: hangisinin kırıldığı ayrı görünüyor.
  - Action sürümleri GitHub'dan kontrol edildi: `checkout@v7`, `cache@v6`, `upload-artifact@v7`.
- **Kalite kapısı:** `--min-recall5` ve `--min-evidence5` bayrakları; eşik altında eval hata koduyla çıkıyor. Eşikler önce CI'da ölçülüp sonra kondu.
- **İlk CI ölçümü** (GitHub Actions, Linux x86_64, CPU):
  - Recall@5 0,768, MRR 0,509, evidence recall@5 0,587; **41 sorunun hiçbirinde sıralama Mac'ten (M4, MPS) farklı değil.**
  - Vektöre çevirme 217 sn (M4'te 25 sn); iş toplam ~4 dk.
  - Eşikler: Recall@5 ≥ 0,74, evidence recall@5 ≥ 0,55 (yaklaşık bir soru aşağısı). Tam mevcut değer seçilmedi: bir sorunun bir sıra kayması CI'ı kırar ve başka yerde kazanç getiren bilinçli değişiklikleri engellerdi. Eşik ancak bilerek, gerektiren değişiklikle birlikte düşürülür.
- **İyileştirme fırsatı (yapılmadı):** Vektörler chunk özeti + model adıyla önbelleğe alınırsa her koşuda 3,5 dk kazanılır (ör. Qdrant'ın diske yazan yerel modu + `actions/cache`). Şimdilik erken optimizasyon.

### D43. HTTP API: FastAPI, zincir başlangıçta bir kez kuruluyor
- **Neden FastAPI:** İstek ve yanıt şemaları Pydantic ile tanımlanıyor; gelen JSON otomatik doğrulanıyor (boş soru → 422). `/docs` adresinde etkileşimli dokümantasyon kendiliğinden oluşuyor. İş ilanlarında en sık geçen Python API çatısı.
  - Alternatifler: Flask (şema doğrulama ve otomatik dokümantasyon yok, elle yazılır), Django (bir API için fazla ağır).
- **Uç noktalar** (`app/api.py`):
  - `POST /ask`: cevap, türü (answer/partial/refusal), İngilizce sorgu, kaynaklar (etiket, makale, sayfalar, bölüm, chunk metni), uydurma etiketler, süre, modeller. `app.ask`'ın ekrana yazdığı her şey JSON olarak.
  - `GET /health`: Qdrant'taki indeksin nokta sayısı; ulaşılamazsa 503.
- **Zincir bir kez kuruluyor:** FastAPI'nin `lifespan` mekanizmasıyla, uygulama açılırken. Embedding modelini yüklemek ~11 sn sürüyor; her istekte tekrarlanmıyor.
- **Uç nokta senkron (`def`):** `chain.invoke` senkron. FastAPI senkron uç noktaları ayrı bir iş parçacığı havuzunda çalıştırıyor; bir istek LLM'i beklerken diğerleri bloklanmıyor. `async def` kullanılsaydı senkron çağrı olay döngüsünü (event loop) kilitlerdi.
- **Hata kodları:** LLM sunucusuna ulaşılamazsa (`openai.APIConnectionError`, `APITimeoutError`) 500 değil **503** dönüyor. "Sunucu hatası" yerine "bağımlı servis yok" bilgisi veriliyor.
- **Test edilebilirlik:** `create_app(engine_factory)` testlerde sahte bir motor (sahte LLM ve retriever) alıyor. 8 test Ollama, Qdrant ve `.env` olmadan çalışıyor. Bunun için iz kaydı açık değilse `flush()` çağrılmıyor; `flush()` ayarları okuyup `.env` istediği için CI'da kırılırdı.
- **Gerçek deneme** (Apple M4, qwen3:4b-instruct, `dense_tr_bm25_en`): Başlangıç ~11 sn. `/health` 1734 chunk gösterdi. QLoRA sorusu 10,1 sn'de doğru ve kaynaklı cevaplandı; uydurma etiket yok.
