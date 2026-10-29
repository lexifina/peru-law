# Peru: law history in git

The law of Peru as a git history: one file per provision, one commit per law on the day it took effect, and the law that made each change as the commit's author. `git blame` names the law behind every paragraph; `git log` lists every change to an article; checking out a date gives the text in force that day.

It follows the shared design of [lexifina/global-law](https://github.com/lexifina/global-law), which places it at `pe/`.

**What is in it now**

| Folder | Act | Versions | History |
| --- | --- | ---: | --- |
| `constitucion/` | Constitución Política del Perú (1993) | 33 | From its entry into force (31 December 1993) to the bicameral reform in force since 12 April 2026: 37 reform laws, one ruling of the Tribunal Constitucional, and one change no law explains |
| `codigo-civil/` | Código Civil (Decreto Legislativo 295) | 26 | From 25 December 2012 (the oldest text the Ministry of Justice's 14th official edition reaches) to Ley 32228 (January 2025) |
| `proteccion-datos-personales/` | Ley 29733, Ley de Protección de Datos Personales | 3 | As enacted (July 2011) to Decreto Legislativo 1353 (2017) |
| `codigo-procesal-penal/` | Código Procesal Penal (Decreto Legislativo 957) | 79 | As enacted (July 2004), with its district-by-district entry into force, to Ley 32374 (June 2025) |
| `codigo-consumidor/` | Código de Protección y Defensa del Consumidor (Ley 29571) | 20 | As enacted (in force 2 October 2010) to Ley 32495 (November 2025): 19 amending laws and decretos legislativos |

The per-act `README.md` in the folder lists every provision, how often it changed and when. A part is published here only once it has been checked against the official text; `REPRODUCE.md` lists, act by act, the sources and every decision.

## A lawyer's questions as git commands

| Question | Command |
| --- | --- |
| What did art. 112 say on 1 November 2021? | `python tools/vigente_el.py 2021-11-01 constitucion 112` |
| The same, with raw git (bash) | `git show $(git rev-list -1 --before="2021-11-01T23:59:59Z" main -- constitucion/art-112.md):constitucion/art-112.md` |
| The same, in PowerShell | `$r = git rev-list -1 --before="2021-11-01T23:59:59Z" main -- constitucion/art-112.md; git show "$($r):constitucion/art-112.md"` |
| Which law wrote each paragraph of art. 2? | `git blame constitucion/art-002.md` |
| Every change to art. 90, word by word | `git log -p --word-diff constitucion/art-090.md` |
| Every law in the record, in order | `git log --reverse --format="%ad %an" --date=short main` |
| Everything one law changed | `git show law/ley-31988` (tags `law/<key>` mark each law's commit) |
| The whole Constitution on a date | `python tools/vigente_el.py 2000-01-01 constitucion` |
| Laws passed but not yet in force | `git log main..futuro` (empty on 28 October 2026) |

After a rebuild, refresh tags with `git fetch --force --tags`: a plain fetch keeps stale tags.

Files: `preambulo.md`, `art-001.md` ... `art-206.md` (with `art-007-a`, `art-014-a`, `art-034-a`, `art-039-a`, `art-090-a`, `art-102-a`, `art-102-b`), the Disposiciones Finales y Transitorias `dft-01` ... `dft-16`, the Disposiciones Transitorias Especiales `dte-01` ... `dte-04`, and `declaracion.md`.

## Dates

- Each commit is dated at **noon, America/Lima, on the day the change took effect**. Publication and enactment dates are trailers (`Published:`, `Enacted:`); the in-force day is in `In-force:`, which the tools read.
- **Default rule.** Constitución, art. 109: "La ley es obligatoria desde el día siguiente de su publicación en el diario oficial, salvo disposición contraria de la misma ley que posterga su vigencia en todo o en parte." Every reform is dated from the day after its publication in El Peruano unless the law says otherwise.
- **The Constitution of 1993** was ratified by referendum on 31 October 1993, promulgated on 29 December 1993 and published in El Peruano on 30 December 1993. Its first commit is dated 31 December 1993.
- **Ley 31988** (bicameral Congress, published 20 March 2024) says its reforms "entran en vigor a partir de las próximas elecciones generales". They are dated 12 April 2026, the day of the general elections as convened by [Decreto Supremo 039-2025-PCM](https://busquedas.elperuano.pe/dispositivo/NL/2384222-1), art. 1 (El Peruano, 26 March 2025), together with its repeal of art. 90-A.
- **Ley 29402** (art. 90, 130 congresistas) is dated from the day after publication (9 September 2009); its own transitional provision makes it apply to the 2011 elections, as its commit message says.
- **STC 918/2021** of the Tribunal Constitucional (11 November 2021) declared Leyes 31280, 31304 and 31305 unconstitutional. It was published on 26 November 2021 and rules from the next day without retroactive effect, so the earlier text of arts. 112, 21 and 2 returns on 27 November 2021.
- `--before="YYYY-MM-DD"` alone uses your clock's time of day, so a law that took effect that day may be missed before noon. Use `T23:59:59Z` as above, or the tool.

## How it is checked

- **Against the official consolidated text.** On the day before Ley 31988 took effect, every provision in the repository matches the Congreso's December 2024 edition exactly, except art. 91, where that edition prints numeral 3 twice (as numerals 3 and 4); no reform did that, so the May 2021 wording is kept. The May 2021 edition also matches on its date, except art. 39 (see below) and one paragraph break in art. 56.
- **Against the laws themselves.** Every paragraph that Leyes 31118, 31280, 31304, 31305, 31414, 31507, 31878, 31988, 32135, 32145, 32188 and 32189 added or changed was found word for word in the text of the law as published in the Archivo Digital de la Legislación del Perú (169 paragraphs; `tools/verify_laws.py`). Older laws are scans without a usable text layer.
- **Against earlier editions.** Each rebuilt state is compared word by word with the Congreso editions of 2004 (a copy not updated after 1995), 2012, 2015, February 2019 and April 2019. The remaining differences are editorial variants between editions, each listed in `REPRODUCE.md` ("las listas"/"la lista" in art. 90, "a Congreso"/"al Congreso" in art. 96, and the like).
- **Against El Peruano of 30 December 1993.** The scanned gazette was read for the points where sources disagree (see "unexplained" below) and for the original Chapter XIV.
- **Código de Protección y Defensa del Consumidor.** Rebuilt backwards from the Ministry of Justice's third official edition (current to 27 November 2020), whose notes quote the wording before each amendment; the state on that date equals the edition exactly. The rebuilt text on 31 May 2018 equals the second official edition word for word in all 178 provisions. Later laws are replayed from their own texts (Congreso ADLP), every paragraph checked word for word in the law; on 15 August 2024 the result equals Editora Perú's consolidated text in 169 of 171 articles (art. 88: Editora Perú had not yet inserted Ley 31763; art. V: a spelling variant).
- Every version is read back from git on the day it took effect and on the day before (`tools/check_repo.py`); both must match `corpus.json`. Commit dates never go backwards, there are no merges, nothing is dated in the future, and every trailer parses. The repository is rebuilt a second time and must give identical hashes. Results are in `REPRODUCE.md`.

## What "author" means

The author of a commit is the law that made the change, with an e-mail address that cannot exist (`ley-31988@congreso.gob.pe.invalid`), so `git blame` and `git log --author` name laws. The committer is always Lexifina.

- **Credits come only from the source.** A provision is credited to a law only when the Congreso's own notes say that law changed it ("Artículo modificado por Ley 28607, publicada el 4 de octubre de 2005. Antes de la reforma, este artículo tuvo el siguiente texto: ..."), or when the law itself does.
- **The Tribunal Constitucional** is the author of the commit that restores the text of arts. 2, 21 and 112 after STC 918/2021.
- **Leyes 27600 and 32265** removed (2001) and restored (2025) the signature of Alberto Fujimori on the Constitution. They change no provision's words; each is a commit marked `Words-changed: no`, attached to the preamble.
- **One change is unexplained** and committed by the publisher, the Congreso: the sentence "No son acumulables servicios prestados a la actividad pública y privada." at the end of the Segunda Disposición Final y Transitoria. It is in the Congreso's 2021 and 2024 editions but not in El Peruano of 30 December 1993 (page 15), the Congreso's editions of 2004 to 2019, or the ADLP text, and no reform law added it. It is dated 1 May 2021, the month of the first edition that has it.
- **Art. 39** reads "Junta Nacional de Justicia" in the 2024 edition, applying the renaming in Ley 30904's Única Disposición Complementaria Final; the 2021 edition still printed "Consejo de la Magistratura". The change is credited to Ley 30904 on its in-force day, 11 January 2019. Other articles that still name the "Consejo Nacional de la Magistratura" in the 2024 edition are left as printed.
- Blame credits whole lines (one paragraph per line). In a provision written by several laws, use `git log -p --word-diff` to see exactly which words each law changed.

## What it does not show

- **Section headings** (títulos and capítulos, such as the heading of Chapter VI of Title III changed by Ley 32189) are not tracked yet.
- **Paragraph breaks in rebuilt texts.** Earlier wordings come from quotations in the Congreso's notes, set in small type; where a quotation's paragraph breaks cannot be read from the layout, they are inferred. Words are checked; breaks may differ from El Peruano.
- **Spelling of the original.** The texts are the Congreso's editions, not a transcription of El Peruano; small differences of capitalisation from the 1993 gazette may remain (for example "la Ley"/"la ley" in the original art. 192).
- **Reforms after Ley 32265.** No Congreso edition after December 2024 exists, and the Congreso's list of reform laws names none after Ley 32265 (22 March 2025) as of 28 October 2026.
- **Código de Protección y Defensa del Consumidor:** changes made by decretos legislativos or by laws whose title does not name the Code after April 2025, and anything after Ley 32537 (26 December 2025), where the Congreso's law index ends. Ley 31763 starts "a los sesenta días hábiles"; no official source gives the day, so it is counted (29 August 2023; see `REPRODUCE.md`). The later start of arts. 36-37 and of the summary procedure in 2010-2011 is described, not committed.
- **SPIJ**, the Ministry of Justice's consolidated legislation, was not used: it does not answer from outside Peru's networks here, and full access is paid.

## How it is built

`tools/fetch.py` downloads every source once through curl (one request per second per host, cached by the sha256 of the URL); `tools/editions.py` reads the Congreso's PDF editions with PyMuPDF, using type size and position to separate the text from the notes; `tools/parse.py` rebuilds the history and writes `corpus.json`; the shared builder `tools/build.py` writes the history with `git fast-import`. `REPRODUCE.md` records every command, data hash and decision.

The history is rebuilt like this:

1. The Congreso's May 2021 edition carries, for each reform up to Ley 31122, a footnote quoting the provision's earlier text. Undoing them in turn, from the 2021 text, gives every earlier version back to 1993.
2. Where those notes quote nothing (the original Chapter XIV replaced by Ley 27680, arts. 191 and 194 before Ley 28607, numeral 3 of art. 91 before Ley 28484, numeral 6 of art. 203 before Ley 30305, art. 40 before Ley 31122), the Congreso's 2012 consolidation supplies the text.
3. Later reforms come from the December 2024 edition; Leyes 31280, 31304 and 31305, which no edition carries, from the laws as published; Ley 31988 from the 2024 edition's notes, which quote its future text.

No AI model wrote or changed legal text. Claude Opus 5.5 wrote the scripts and chose the sources; see `REPRODUCE.md`.

## Sources

| Source | Kind | Past versions | Names the amending act | Bulk | Notes |
| --- | --- | --- | --- | --- | --- |
| [Congreso de la República: ediciones de la Constitución](https://www3.congreso.gob.pe/Docs/files/constitucion/constitucion-12-2024.pdf) | Official consolidated text | through notes quoting earlier text (2021 edition) | yes, a note per provision | PDF | Used. December 2024 edition live; May 2021 and older editions (2004, 2012, 2015, 2019) through Internet Archive captures, pinned in `tools/parse.py` |
| [Archivo Digital de la Legislación del Perú](https://www.leyes.congreso.gob.pe) | Official laws | n/a | n/a | PDF per law, title search | Used for the reform laws, the 1993 gazette scan and the 2013 text |
| [Leyes de reforma constitucional](https://www3.congreso.gob.pe/diariodebates/leyesrefconstit/) | Congreso list | n/a | yes | HTML | Used to confirm the list of reforms |
| [Tribunal Constitucional](https://tc.gob.pe/jurisprudencia/2021/00019-2021-AI.pdf) | Ruling | n/a | n/a | PDF | STC 918/2021 |
| [El Peruano, Normas Legales](https://busquedas.elperuano.pe/dispositivo/NL/2384222-1) | Official gazette | n/a | n/a | HTML | Decreto Supremo 039-2025-PCM, the in-force day of Ley 31988 |
| [Ministerio de Justicia: ediciones oficiales](https://www.gob.pe/institucion/minjus/colecciones/2135-ediciones-oficiales) | Official consolidated editions | through "Texto anterior" notes | yes, a note per change | PDF | Used for the Código Civil, Código Procesal Penal and Código de Protección y Defensa del Consumidor (2nd edition 2018 through an Internet Archive capture of SPIJ, 3rd edition 2020 on gob.pe) |
| [Editora Perú, Normas Legales Actualizadas](https://diariooficial.elperuano.pe/Normas) | Consolidated text (state publisher) | no | yes | PDF | Checkpoints through Internet Archive captures (the live files are now served corrupted) |
| [SPIJ](https://spij.minjus.gob.pe) | Official legislation (Ministry of Justice) | n/a | n/a | no | Not used: no answer from here; full access needs a paid licence |
| [Duvet05/Constitucion-Politica-del-Peru](https://github.com/Duvet05/Constitucion-Politica-del-Peru) | Volunteer git repo | yes | partly | n/a | Prior art, for reconciliation only; no text copied |

Research guides that cover every country: [GlobaLex](https://www.nyulawglobal.org/globalex/) and the [Law Library of Congress Guide to Law Online](https://www.loc.gov/research-centers/law-library-of-congress/researcher-resources/guide-to-law-online/).

## Licence

The legal texts are official texts of the Republic of Peru, as published by the Congreso de la República and the Ministerio de Justicia y Derechos Humanos. Fuente: Congreso de la República del Perú (www.congreso.gob.pe; www.leyes.congreso.gob.pe); Ministerio de Justicia y Derechos Humanos, ediciones oficiales (www.gob.pe/minjus). Some sources were read through Internet Archive captures (web.archive.org), pinned in `REPRODUCE.md`. Decreto Legislativo 822, art. 9, excludes official legislative texts from copyright protection. The arrangement, tables, commit messages and tools are by Lexifina, under the terms in `LICENSE`.

This repository is not legal advice and not an official publication.

## En español

Historia de la Constitución Política del Perú de 1993 en git: un archivo por disposición y un commit por norma, fechado el día de su entrada en vigencia y firmado por la norma que hizo el cambio (`git blame` nombra la ley de cada párrafo). Va desde su entrada en vigencia el 31 de diciembre de 1993 hasta la reforma bicameral (Ley 31988), vigente desde las elecciones generales del 12 de abril de 2026 (Decreto Supremo 039-2025-PCM): 37 leyes de reforma y la STC 918/2021 del Tribunal Constitucional.

- Texto vigente en una fecha: `python tools/vigente_el.py 2021-11-01 constitucion 112`
- Fechas: el día siguiente de la publicación en El Peruano (art. 109 de la Constitución), salvo que la ley disponga otra cosa.
- Autoría: cada cambio se atribuye a una ley solo cuando las notas de la edición del Congreso ("Antes de la reforma, este artículo tuvo el siguiente texto") o la propia ley lo indican. La única frase que ninguna ley explica (Segunda Disposición Final y Transitoria) figura a nombre del Congreso como "unexplained".
- Fuente: Congreso de la República del Perú, ediciones de la Constitución de mayo de 2021 y diciembre de 2024, y Archivo Digital de la Legislación del Perú. No se usó el SPIJ. Ningún modelo de IA escribió texto legal.
- También contiene el Código Civil, la Ley 29733 de Protección de Datos Personales, el Código Procesal Penal y el Código de Protección y Defensa del Consumidor (Ley 29571, desde su entrada en vigencia el 2 de octubre de 2010 hasta la Ley 32495), reconstruidos a partir de las ediciones oficiales del Ministerio de Justicia y del texto de cada ley modificatoria.
