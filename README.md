# Peru: law history in git


The law of Peru as a git history: one file per provision, one commit per version on the day it took effect, and the law that made each change as the commit's author. `git blame` names the law behind every paragraph; `git log` lists every change to an article; picking a date gives the text in force that day.

Part of [lexifina/global-law](https://github.com/lexifina/global-law), one git history for every country's law: this is Peru's national law, which global-law reads at `peru/national/acts/`.

**What is in it now:** the Constitution of 1993, 9 codes and 53 other laws and decrees, 63 acts in all, with 377 versions that took effect between 31 December 1993 and 2 August 2026; 2 more, made by Ley 32701 and due on 1 January 2027, are on the `futuro` branch. [`data/versions.json`](data/versions.json) lists every act with the day each version took effect; [`data/laws.csv`](data/laws.csv) lists the 361 laws and decrees and the one ruling in the record, with their dates.

Each act is a folder named after it (`constitucion/`, `codigo-penal/`; `ley-productividad-competitividad-laboral/` is the Texto Único Ordenado of Decreto Legislativo 728, the main labour law), with one file per article or provision (`constitucion/art-112.md` is Article 112 of the Constitution, on the presidential term) and a `README.md` listing its provisions and how often each changed.

The text is in Spanish, as the Congreso, the Ministerio de Justicia, Editora Perú and El Peruano print it. An English translation is not part of this record.

## Questions as git commands

| Question | Command |
| --- | --- |
| Every change to Article 112 of the Constitution | `git log -p --word-diff -- constitucion/art-112.md` |
| Which law wrote each line of Article 112? | `git blame constitucion/art-112.md` |
| Every version of the Constitution, with the day each took effect | `git log --format="%h %(trailers:key=In-force,valueonly,separator=) %an" -- constitucion ":^constitucion/README.md"` |
| Article 112 as in force on 1 November 2021 | `python tools/vigente_el.py 2021-11-01 constitucion 112` |

**Outside git**, we also host this record publicly, for free:

- **[Ask Claude about Peruvian law](https://global-law.lexifina.com/v1/try_claude?country=peru)**: opens Claude with a first question ready.
- **[Ask ChatGPT](https://global-law.lexifina.com/v1/try_chatgpt?country=peru)**: the same question in ChatGPT.
- **[Search Peruvian law on our site](https://lexifina.com/law?country=peru&q=descanso+vacacional)**: a search for "descanso vacacional" (annual leave), with each provision's text and its versions, no account needed.
- **[Developer REST API](https://global-law.lexifina.com/v1/search_law?query=descanso+vacacional&jurisdiction=peru)**: the same search as JSON, with no key. See the [documentation here](https://lexifina.com/api/global-law).

Both assistants read the record through the free Global law connector (MCP, `https://global-law.lexifina.com/mcp`); the first time, the chat gives you the link that adds it. Ask in Spanish or in English.

**Host it yourself easily.** All it takes is git and Python, and the tools run on your machine:

```sh
git clone --depth 1 https://github.com/lexifina/global-law && cd global-law
python3 tools/countries.py add peru/national/acts
python3 tools/law.py show 2026-01-01 peru/national/acts/constitucion/art-112.md
```

Opened in Claude Code, Cursor, VS Code or Codex, the clone also starts a local MCP server with the same tools ([MCP.md](https://github.com/lexifina/global-law/blob/main/MCP.md)).

## Dates

Each commit is dated at noon, America/Lima, on the day the change took effect, and carries it in its `In-force:` trailer, beside `Enacted:` and `Published:`:

- a law is in force from the day after its publication in El Peruano, unless it postpones that day in whole or in part (Constitución, art. 109); a law that waits for its reglamento is dated from the day it says (Ley 32123 from 6 September 2025, the day after Decreto Supremo 189-2025-EF was published);
- the reforms of Ley 31988 (a two-chamber Congress), in force "a partir de las próximas elecciones generales", are dated 12 April 2026, the election day set by Decreto Supremo 039-2025-PCM;
- STC 918/2021 of the Tribunal Constitucional, published on 26 November 2021, applies from the next day, so the earlier text of arts. 2, 21 and 112 returns on 27 November 2021.

Each change is credited to the law, decree or ruling that made it, with an address that cannot exist (`Ley 31988 <ley-31988@congreso.gob.pe.invalid>`), and only where the source's notes or the law itself say so; the committer is Lexifina. An act that starts from a consolidated text starts with the "oldest version available", credited to its publisher (Editora Perú for 49 of the 51); one sentence of the Constitution that no law explains is credited to the Congreso.

## How it is checked

- `tools/check_repo.py` reads every version back from git on the day it took effect and on the day before, and compares it with the corpus whose sha256 is in `data/corpus.sha256`: 379 versions of 63 acts, 0 mismatches; every commit's trailers parse, `main` has no merge commits and nothing is dated in the future (see [`REPRODUCE.md`](REPRODUCE.md)).
- The Constitution's earlier texts come mostly from the notes of the Congreso's 2021 edition; each state is compared with the Congreso's editions of 2004 to 2024, and every paragraph changed by twelve reform laws since 2021, Ley 31988 among them, was found word for word in the law as published.
- For the other acts, the first version is checked provision by provision against its official edition or Editora Perú's consolidated text, and each later change is the amending norm's own wording in El Peruano, compared with a later consolidation where one with a usable text layer exists. Every ley, decreto legislativo and decreto de urgencia published in a period `REPRODUCE.md` gives for each act, up to 31 October 2026, was read for changes.
- The same corpus gives the same commit hashes (`tools/build.py`); no second build has been compared yet. History is append-only (`tools/append.py`): no published commit is rewritten.

## What it does not show

- **Most of Peru's law.** 63 acts are here; reglamentos and other decretos supremos, most decretos legislativos, regional and municipal ordinances and case law are not (STC 918/2021 is here only as the commit that restored three articles).
- **History before an act's first version.** 51 of the 63 acts start from a consolidated text (the Código Civil from 2012, the Código Penal from 2016, most others from 2020 to 2026), not from their publication; earlier changes are inside that first version.
- **Section headings** (títulos, capítulos) are not tracked.
- **Laws waiting for their reglamento.** Leyes 32195 and 32329 (Código Penal) and 32353 (Ley General de Inspección del Trabajo) take effect the day after a reglamento not published by the end of October 2026, so their changes are left out.
- **Paragraph breaks** in the Constitution's earlier texts are inferred from the notes that quote them; their words are checked, the breaks are not.

## Sources

| Source | Kind | Past versions | Notes |
| --- | --- | --- | --- |
| [Congreso de la República, ediciones de la Constitución](https://www3.congreso.gob.pe/Docs/files/constitucion/constitucion-12-2024.pdf) | Official consolidated text | yes, through notes quoting the earlier text | The editions of May 2021 and December 2024; older ones (2004 to 2019) through Internet Archive captures |
| [Archivo Digital de la Legislación del Perú](https://www.leyes.congreso.gob.pe) | Official laws (Congreso) | n/a | The text of the reform laws and the 1993 gazette scan |
| [Ministerio de Justicia, ediciones oficiales](https://www.gob.pe/institucion/minjus/colecciones/2135-ediciones-oficiales) | Official consolidated editions | yes, through "Texto anterior" notes | The Código Civil, Código Penal, Código Procesal Penal and Código de Protección y Defensa del Consumidor |
| [Editora Perú, Normas Legales Actualizadas](https://diariooficial.elperuano.pe/Normas) | Consolidated text (state publisher) | no | The first version of most other acts, and checkpoints; read through Internet Archive captures |
| [El Peruano, Normas Legales](https://busquedas.elperuano.pe) | Official gazette | n/a | The text of the amending laws and decrees |
| [Tribunal Constitucional](https://tc.gob.pe/jurisprudencia/2021/00019-2021-AI.pdf) | Ruling | n/a | STC 918/2021 |

## Licence

See [`LICENSE`](LICENSE). Decreto Legislativo 822 (Ley sobre el Derecho de Autor), art. 9, excludes official texts of a legislative, administrative or judicial nature from copyright protection. Lexifina's own contributions (the arrangement of the history, the commit messages, the tables and the tools) are dedicated to the public domain under CC0 1.0.

No AI model wrote, translated or corrected legal text, and none runs at build time; the scripts were written by Claude Code running Claude Opus 5.5 (see [`REPRODUCE.md`](REPRODUCE.md)).

## En español

Historia del derecho peruano en git: un archivo por disposición y un commit por versión, fechado el día de su entrada en vigencia y firmado por la norma que hizo el cambio. Contiene la Constitución de 1993, con toda su historia desde el 31 de diciembre de 1993, nueve códigos y otras 53 leyes y decretos, con 377 versiones; 51 de las 63 normas parten de un texto consolidado, no de su publicación original. Texto vigente en una fecha: `python tools/vigente_el.py 2021-11-01 constitucion 112`.

## More

From [lexifina/global-law](https://github.com/lexifina/global-law):

- [FEATURES.md](https://github.com/lexifina/global-law/blob/main/FEATURES.md): every feature, and what every corpus must support (`git blame`, `law.py`, the MCP tools)
- [FAQ.md](https://github.com/lexifina/global-law/blob/main/FAQ.md): questions and answers · [CONTRIBUTING.md](https://github.com/lexifina/global-law/blob/main/CONTRIBUTING.md): proposing changes · [MCP.md](https://github.com/lexifina/global-law/blob/main/MCP.md): the MCP server · [REPRODUCE.md](https://github.com/lexifina/global-law/blob/main/REPRODUCE.md): how it was built · [CHANGELOG.md](https://github.com/lexifina/global-law/blob/main/CHANGELOG.md)
- [FRESHNESS.md](https://github.com/lexifina/global-law/blob/main/FRESHNESS.md): how current each corpus is · [Monitoring](https://github.com/lexifina/global-law/tree/main/monitoring): whether updates are running · [WATCHING.md](https://github.com/lexifina/global-law/blob/main/WATCHING.md): how each official source is watched for changes
- [performance/](https://github.com/lexifina/global-law/tree/main/performance): how fast the tools are, measured
- [visualisations/](https://github.com/lexifina/global-law/tree/main/visualisations): charts and bridges across the world's law
- [Vulnerabilities](https://github.com/lexifina/global-law/tree/main/vulnerabilities): mistakes in legislation as published
