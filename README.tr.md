<p align="center">
  <img src="assets/clawmuse.png" alt="clawmuse logo" width="240">
</p>

# clawmuse

[English](README.md)

Claude Code eklentisi. Araştırma ve test işlerini **Muse**'a (Meta'nın Muse Spark kod ajanı, `muse` CLI) devrederek Claude'un daha az token harcamasını sağlar.

Claude kısa bir görev tarifi yazar. Dosya okuma, arama, web araştırması ve test çalıştırmayı Muse kendi kotasıyla yapar. Claude'un bağlamına yalnızca Muse'un kısa raporu girer. Bu rapor genelde birkaç bin karakterdir; Muse'un okuduğu ise on binlerce, bazen yüz binlerce karakter olur.

## Nasıl çalışır

| Parça | Görevi |
| --- | --- |
| `bin/muse-ask` | `muse exec --json`'u başsız çalıştırır, yalnızca Muse'un son raporunu ve tek satırlık özeti basar. Eklenti açıkken `PATH`'tedir. |
| `skills/muse` | Claude'a ne zaman devredeceğini ve görev tarifini nasıl yazacağını anlatır. Yalnızca kullanılınca yüklenir. |
| SessionStart hook'u | Her oturumun başında Claude'a Muse'un hazır olduğunu söyler. |
| UserPromptSubmit hook'u | Mesajında Muse geçerse, o mesajda devretmeyi Claude'un kararına bırakmaz, zorunlu kılar. |

Düzenlemeyi ve son doğrulamayı yine Claude yapar. Muse yalnızca araştırır ve komut çalıştırır.

## Gereksinimler

- Eklenti desteği olan bir Claude Code.
- Muse Code: `muse` CLI kurulu ve giriş yapılmış olmalı. Terminalde `muse exec` çalışmalı.
- Python 3.8 veya üstü; `python3`, `python` ya da Windows'taki `py` komutuyla çalışabilmeli. Microsoft Store kısayolları atlanır.
- Linux, macOS ya da Windows. Windows'ta Claude Code eklentinin betiklerini Git Bash ile çalıştırır.

`muse` kurulu değilse hook'lar hiçbir şey eklemez, Claude her zamanki gibi çalışır.

## Kurulum

Claude Code içinde:

```
/plugin marketplace add codezzium/clawmuse
/plugin install clawmuse@clawmuse
```

Ya da terminalden:

```
claude plugin marketplace add codezzium/clawmuse
claude plugin install clawmuse@clawmuse
```

Kurduktan sonra yeni bir oturum aç. Güncellemeleri almak için `/plugin` menüsünde `clawmuse` mağazasının otomatik güncellemesini aç ya da `claude plugin update clawmuse@clawmuse` çalıştır.

## Kullanım

- **Kendiliğinden:** Normal çalış. Birkaç dosyaya yayılan sorularda ("X nerede, nasıl çalışıyor"), web ve doküman araştırmasında, test ya da derleme çalıştırmada ve uzun loglarda Claude işi kendisi devreder.
- **Adını anarak:** Mesajında Muse geçerse o mesajda devretmek zorunlu olur. Örnek: *"önbelleğin nerede geçersiz kılındığını Muse'a araştırt, sonra düzelt"*.
- **Açıkça çağırarak:** `/clawmuse:muse test birim testlerini çalıştır ve hataları özetle`.

### muse-ask

```
muse-ask [-m research|test] [-C DIZIN] [-w KELIME] [-t SANIYE] [-c OTURUM] [-i RESIM] "görev"
```

| Seçenek | Anlamı |
| --- | --- |
| `-m research` | Varsayılan. Muse'un dosya yazma araçları kapalıdır ve hiçbir şeyi değiştirmemesi söylenir. |
| `-m test` | Test, derleme ve konteyner çalıştırabilir. Kaynak kodu düzenleyemez, commit ve deploy yapamaz. |
| `-C DIZIN` | Muse'un çalışacağı dizin. Varsayılan: bulunulan dizin. |
| `-w KELIME` | Rapor için kelime sınırı. Varsayılan: 300. |
| `-t SANIYE` | Muse bu kadar saniye sonra durdurulur. Varsayılan: 540. |
| `-c OTURUM` | Önceki bir Muse oturumunda takip sorusu sorar. Muse daha önce okuduklarını hatırlar. |
| `-i RESIM` | Görsel ekler. Birden çok kez verilebilir. |

Muse her zaman `muse-spark-1.3` modeliyle ve `max` effort ile çalışır. Bu bilerek sabitlendi: ne Claude ne kullanıcı çağrı başına değiştirebilir.

Görev tarifi stdin'den de verilebilir: `muse-ask -m test - <<'EOF' … EOF`.

Özet satırında mod, geçen süre, araç çağrısı sayısı, Muse'un okuduğu karakter sayısı, oturum kimliği ve log yolu yer alır. Muse'un gördüğü her araç çıktısı 7 gün boyunca `~/.cache/clawmuse/runs/*.md` altında saklanır. Böylece Claude bir şeyi yeniden çalıştırmak yerine loglarda arama yapabilir.

Çıkış kodları:

| Kod | Anlamı |
| --- | --- |
| 0 | Rapor geldi |
| 1 | Muse hata verdi |
| 2 | Kullanım hatası ya da Muse'un içinden yapılan iç içe çağrı |
| 124 | Zaman aşımı. Kaldığı yerden devam etmek için ipucu basılır. |
| 127 | `muse` bulunamadı |
| 143 | Kesildi |

## İzinler

Muse her zaman `--yolo` ile çalışır: sandbox yoktur, onay sorulmaz. Başsız çalıştırmada onay verecek kimse olmadığı için böyledir. Muse, kullanıcı hesabının çalıştırabildiği her komutu çalıştırabilir.

Araştırma modunda Muse'un dosya yazma araçları kapalıdır ve hiçbir şeyi değiştirmemesi söylenir, ama kabuk komutları engellenmez. Eklentiyi ancak bunu kabul ediyorsan kur.

## Örnek ölçümler

Bunlar tek bir React Native oyun reposunda yapılmış tekil denemelerdir, kıyaslama testi değildir.

| İş | Muse'un okuduğu | Claude'a dönen |
| --- | --- | --- |
| İstemci test takımının tamamı (528 test) | 44 bin karakter | 0,7 bin karakter |
| 3 kaynak dosyaya yayılan "yerleştirme animasyonları nasıl çalışıyor?" sorusu | 68 bin karakter | 3 bin karakter |
| Eklenti dağıtımı üzerine web araştırması (30'dan fazla sayfa) | 297 bin karakter | 4,5 bin karakter |

Aynı kod sorusu başsız bir Claude oturumuna da soruldu:

| | Tur | Maliyet | Süre |
| --- | --- | --- | --- |
| Muse olmadan | 16 | 0,44 $ | 60 sn |
| Muse ile | 8 | 0,28 $ | 150 sn |

Devretmek zaman alır. Bu yüzden tek dosyalık hızlı bakışları Claude kendisi yapar.

## Geliştirme

```
claude --plugin-dir /eklentinin/yolu        # yerel değişiklikleri tek oturumda dene
```

Kurulan kopyalar önbelleğe alınır. Değişiklik yayınlarken `.claude-plugin/plugin.json` içindeki `version` değerini artır; artırmazsan kullanıcılara ulaşmaz.

## Lisans

MIT. Ayrıntılar için [LICENSE](LICENSE) dosyasına bak.
