# 3. ajan prototipi (deneme kodu)

**Üretim kodu değil.** 2026-10-03'te 3. ajanın kurallarını (10 ölçü, eşikler, tür, sınıf, fiyat satırı) 10 gerçek ABD
şirketinde denemek için yazıldı. Kurallar: `docs/YOL_HARITASI_v2.md` 3. bölüm · sonuçlar ve öğrenilenler:
`docs/BAGLAM.md` 9. bölüm · dış inceleme: `docs/DIS_INCELEME_PROMPT.md`. Asıl 3. ajan yazılırken buradan fikir alınır,
olduğu gibi kopyalanmaz.

| Dosya | Ne yapar |
|---|---|
| `indir.sh` | SEC verisini indirir (10 deneme şirketi + 5 örnek; `frames` ile tüm şirketler) |
| `karne_deneme.py` | 10 ölçü, tür, sınıf — `python3 karne_deneme.py KO NVDA NKE ...` |
| `fiyat.py` | Yahoo'dan fiyat; PEG ve serbest nakit akışı verimi |
| `ek_uret.py` | Dış inceleme promptunun Ek A / Ek B tablolarını üretir + Yahoo bölünme sağlaması |
| `etiket_kontrol.py` | Hangi XBRL isminin hangi şirkette kaç yıl bulunduğunu gösterir |
| `kapsam_olcum.py` | Eş anlamlılar listesinin ~1.700 şirkette kapsamını ölçer |

Çalıştırma (bu klasörde):

```bash
export SEC_UA="Ad Soyad eposta@ornek.com"   # SEC iletişim bilgisi ister
bash indir.sh
python3 karne_deneme.py KO NVDA NKE SBUX PFE INTC BA SNAP DOW RIVN
uv run --with yfinance python fiyat.py
python3 etiket_kontrol.py AAPL AMZN NET V KO NVO
bash indir.sh frames && python3 kapsam_olcum.py
```

Bilinen sınırlamalar: dış inceleme promptundaki "Bildiğimiz sınırlamalar" listesi.
