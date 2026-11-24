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
