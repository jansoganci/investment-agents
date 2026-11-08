---
doc: PDF reader — decision note
date: 2026-11-07
updated: 2026-11-08 (section 8)
status: discussed, not built
publish: no
---

# PDF reader — decision note

Talk of 2026-11-07. No code, no test, no `settings.yaml` change, no mail sent. Building waits for a separate "yes". Fixed rule 5 still applies: this is not an exception, and it is not the next phase.

This is not the deferred HK / A-share filing reader (roadmap section 9). That one would read a company's own annual report, interim report, or investor presentation into a card. This one reads a broker research PDF and stops at an email.

## 1. What it is

A program inside this repo. I drop a research PDF in Google Drive. The program reads that file alone and sends one formatted email to my own address.

One PDF, one email. A second PDF, even about the same stock, is a new email. Emails do not cite each other. The program does not write a card, a grade, a portfolio row, the Sunday summary, or Telegram.

If I like a stock, I say so later, in my own words: "track this stock." That sentence is the existing follow path. It is not part of this program. It is not built here.

## 2. What was done this night

Six PDFs were read from the repo root, as samples of the input, then moved to `docs/pdf-samples/`. Text was extracted only to see the shape of each file. Nothing was saved as a system output. The bank text is not pasted into this note.

| File | What it actually is |
|---|---|
| `docs/pdf-samples/GE Vernova Inc（GEV.US）：CFO路演要点；跑赢大盘-261104.pdf` | Bernstein, 4 Nov 2026, 13 pages. One US stock (GEV). CFO meeting note. |
| `docs/pdf-samples/摩根士丹利-Nike Inc（NKE.US）：投资者日框架——归一化EPS约2美元；维持减配-261104.pdf` | Morgan Stanley, 4 Nov 2026, 21 pages. One US stock (NKE). Investor-day framework. |
| `docs/pdf-samples/高盛-中国工业科技2027年展望——估值重置，偏好AI机器人与数据中心电气、相对看淡电网技术-261106.pdf` | Goldman Sachs, 6 Nov 2026, 67 pages. China industrial tech sector. Many stocks. |
| `docs/pdf-samples/Memory price tracker.pdf` | Bernstein, 5 Nov 2026, 32 pages. DRAM and NAND prices. Several memory stocks. |
| `docs/pdf-samples/JPM - Japan Equities.pdf` | J.P. Morgan, 5 Nov 2026, 18 pages. The Japanese market. Not one stock. |
| `docs/pdf-samples/GPS-5432065-0.pdf` | J.P. Morgan, 5 Nov 2026, 7 pages. Title: "Türkiye's exports under the hood: More than the lira." No stock. |

The filename does not show the subject. `GPS-5432065-0.pdf` is the Turkey export note. It is one sample among the six, not a Turkey product. It gets its own email, like every other file. A file with no single stock has no "company" line and no "ahead or behind its sector" line. Those lines become the report's own subject and the report's own ranking.

Plain text extraction is not enough. On the Goldman file some words sit in boxes and were missed. Nike's charts did not come out as tables. The memory note's point is in the charts. A later build has to see the page, not only the text stream. Not built.

The six files stay in `docs/pdf-samples/`. They are broker research. They are not committed. Some houses forbid republication and forbid feeding the text into an AI system. The email is a private note: short quotes, my address only, no publishing. That limit is recorded. It is not solved.

## 3. Decisions (mine, 2026-11-07)

1. The program lives in this repo. It is not wired to the card, the portfolio, the Sunday summary, Telegram, or the 10 measures.
2. One PDF is analyzed only inside itself.
3. The output is one email to me. Not a web page. Not Telegram. A long Telegram message was rejected because it would be cut.
4. The email does not say buy or sell. It gives the good side, the bad side, and whether the company is ahead of or behind its sector, as the report says.
5. The 10 measures are not computed from the PDF. They run only after I say "track this stock", and they run on the company's own filing, as they do today.
6. The same five questions are asked of every PDF (section 5). There is no second score.
7. The email shape in section 4 stays. I said "kalsın" to that shape and to the five questions.
8. Which model reads the PDF is not chosen. Mail sending does not exist in this project today. Both wait for a later yes. (2026-11-08: the model is chosen and the mail goes from my own address; see section 8.)

## 4. The email (approved)

People scan a mail in an F. The subject is about six words and states the result. The preview line does not repeat the subject. The result is in the first lines. Detail is below. Sources for that reading: Arizona State University email guide (about eight seconds, inverted pyramid, preview under about 90 characters), Toastmasters, January 2024 (subject about six words, result first, body that can be scanned), Mailsnap (F-shaped scan). Those sources are about mail in general, not about investment results.

Approved Nike example. Every figure is Morgan Stanley's claim in the sample PDF, not a figure of this system. Close on 3 Nov 2026 was $38.48; the mail rounds the price to 38.

**Subject:** Nike sektörün gerisinde

**Preview:** Hedef 25 dolar, fiyat 38. Pay kaybı.

Nike, Morgan Stanley, 4 Kasım 2026.
Sektörüne göre geride. Pay kaybediyor, diyorlar.
İyi: performans yaklaşık 16 milyar dolardan 18 milyara çıkabilir.
Kötü: spor giyim ve Jordan küçülür, diyorlar.
Varsayım: kârın düşmesi marjdan değil, cirodan.
Bankanın hedefi 25 dolar. O günkü fiyat 38. Bu bankanın sayısı.

Below that, still the same PDF: three methods meet near $40 billion of sales. Earnings per share about $2. The street says $2.45. A 67-page PDF keeps the same short first screen. The rest is at most five bullets.

The mail is Turkish. Where the working text is stored, if it is stored, was not decided.

## 5. The five questions (approved)

Asked of every PDF. A missing answer stays blank. Nothing is filled in from another PDF or from the card.

1. Who wrote it, which day, what is it about?
2. What is the claim, in one sentence?
3. Which assumption does that claim rest on? The report can be wrong here even when a number inside it is right.
4. Good side and bad side. Only what the report writes.
5. Ahead of or behind its sector? If the PDF has no single stock, this is the report's own ranking: whom it puts ahead, whom it puts behind.

## 6. Looked up, not added

The question the same night: if Buffett, Lynch, Pabrai, or another investor whose method can be written as rules, built this reader, what would they look at?

They would not add a new score to this email. The number half of their methods is already the card's 10 measures, the price line, PEG, and the free-cash yield. Those are computed from filings, not from a broker PDF.

What can be written down as a rule:

- Joel Greenblatt. Two numbers: return on the capital used in the business, and pre-interest, pre-tax profit divided by enterprise value. Rank, hold a year, rerun. He would not read the story. Banks, insurers, and property companies are outside his formula. The formula can lag for years.
- Terry Smith. A good business, do not overpay, then do nothing. High return on capital for years, profit that arrives as cash, debt that does not swallow the business. He has not published one magic cutoff.
- Peter Lynch. Category, a two-sentence story, price divided by growth. Growth is not the analyst's far-year guess and not one peak year. Very fast growth gets cut. The ratio lies for a cyclical. These rules are already in the roadmap.
- Mohnish Pabrai. The bad case first. If the gain is not large and the loss is not small, he passes. Few positions. "Is there a moat?" is not a program. "Can I live with the bad case?" is.
- Warren Buffett. Owner earnings, not paper profit. Little debt. Share count that does not balloon. The moat and the manager's honesty are not a number. The bank's price target is not his input.

Benjamin Graham's cheapness list and Piotroski's nine yes/no questions are also programs. Both need the company's own statements. A broker PDF does not supply them.

If a PDF happens to state one of these, it goes into the good side, the bad side, or the assumption. If it does not, the line stays empty. Nike, as an example of that reading, not as a new rule: Lynch would ask the category and would not build a PEG from the 2031 guess. Pabrai would ask whether the bad case (sales near $32 billion, earnings per share near $1.40) is survivable. Buffett would ask whether the $2 is cash. This PDF does not answer that. Nike's stock pay is large in the filing, not in this note. Greenblatt would not read the 21 pages. Smith would ask whether the 9.5% margin is ten years of fact or the bank's forecast. In this note it is a forecast.

Patience is part of the method. One email is not one buy.

## 7. Not decided

The list of 2026-11-07, as it stands after section 8. Struck lines are decided.

- ~~The model.~~ Decided, 8.1.
- How the mail is sent. My address is decided (8.2). The kind of Gmail permission is not.
- Which Drive folder receives the PDFs. The flow is decided (8.3). The folder names are not.
- The command name. A run picks up a new file (8.3). How often is not decided.
- ~~Where a copy of the email is kept.~~ Decided, 8.4: nowhere.
- ~~What to do about houses that forbid putting their text into an AI system.~~ Decided, 8.5.
- ~~Whether `.gitignore` should ignore `docs/pdf-samples/`.~~ Decided and done, 8.6.

## 8. Decisions of 2026-11-08 (mine)

Still no code. Building waits for a separate "yes" and for a fixed-rule-5 exception (8.8).

1. **Model:** `gpt-6-sol`, the model already in `settings.yaml` and already working. No new model, no new provider.
2. **Mail:** from my own Gmail address to my own address. I open the access myself.
3. **Flow:** I drop a PDF into a folder in Drive. The system reads it, sends the mail, and moves the PDF to a second folder. The Air already has Drive as a local folder (`DRIVE_DIR` = `Investing/`, the same way the bulletin and the Sunday summary are written), so no Drive API is needed.
4. **No copy:** the content of the mail is not saved anywhere else. The mail is the record. The third folder ("Z", an analysis file next to the PDF) is dropped, because it would hold the same text as the mail.
5. **Houses that forbid AI use:** ignored, by my decision. What still holds: the PDFs never enter git (the repo is public, 8.6), and the mail goes only to me.
6. **`.gitignore`:** `docs/pdf-samples/` is ignored. Done in the same commit as this section.
7. **Claude's proposals, not yet confirmed by me:**
   - folder names `Investing/PDF/New/` → `Investing/PDF/Done/`; after 3 failed reads → `Investing/PDF/Failed/` and a one-line "could not read" mail;
   - Hermes looks at `New/` every 30 minutes (an empty folder costs nothing) and waits until Drive has finished syncing a file;
   - Gmail permission "send only" (the program cannot read my mail; an app password would open the whole mailbox);
   - the PDF goes to the model with its page images, not as plain text (needed for Goldman's boxes and the charts; `shared/ai` sends only text today, so this is a small addition);
   - a code check that every figure in the mail appears in the PDF (no model cost; the bulletin already has a similar check).
8. **Not given yet:** the fixed-rule-5 exception that building needs.

Cost estimate (not measured; the first trial measures it): a 7-page PDF a few cents, a 67-page PDF about 0.20–0.40 $. The system spends about 21 $ a month against the 30 $ limit, so about 25–40 large PDFs a month fit.
