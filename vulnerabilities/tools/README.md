# Tools

The scripts behind this Peru-only run of global-law's vulnerability detectors. They run inside a copy of
[global-law/vulnerabilities/scripts](https://github.com/lexifina/global-law/tree/main/vulnerabilities/scripts) (Python 3.11+,
`pip install duckdb pyarrow`), with a bare clone of this repository at `sources/corpus/peru-law.git`, a blobless bare
clone of global-law at `sources/global-law.git`, and a `pins.json` that names only peru-law, its commit and its
language (`es`). `build_vulns.py`, `flags_chart.py`, `late_ext_select.py`, `late_ext_rebut.py` and `config.json` sit two
folders above the scripts.

| Script | What it does |
| --- | --- |
| `run.sh` | Indexes the history and texts, maps paths to the folders since a move (`map_moved.py`; this repository has not moved its folders, so it changes nothing here), adds this repository's history rows, and runs the detectors (`bash run.sh <shards>`) |
| `add_root.py` | Builds the history rows from this repository's own commits (global-law replays it only up to an earlier commit), so the history detectors read every change |
| `map_moved.py` | Rewrites the paths in the history table to each act's folder after a move of folders (`data/paths.json`, which this repository does not have) |
| `run_triage.sh` | The model review: the 40 strongest flags per category, the 40 strongest lapsed time limits in law texts, and the empty periods (here none) |
| `late_ext_select.py` | Chooses the empty periods for global-law's review of that category (here there were none) |
| `late_ext_rebut.py` | Adds the second, arguing-against pass to the empty-period review, as `triage.py` does for the other categories |
| `build_vulns.py` | Builds `data/flags.csv`, `data/reviewed.csv` and `data/by_category.csv` from the findings and the model review |
| `flags_chart.py` | Draws the chart at the top of the READMEs, in Spanish and English, light and dark |
| `config.json` | The repository, the Spanish category names, the folders and files that are not law, and the chart's labels |
| `patch_detectors.py` | Fixes blind spots found in runs on several country repositories in the copy of global-law's scripts (`python -X utf8 patch_detectors.py <scripts dir>`; a fix already in place is skipped) |
| `patch_detectors_vi.py`, `patch_es.py`, `patch_ca.py`, `patch_en.py`, `patch_de.py`, `patch_en_et.py`, `patch_co.py`, `patch_sv.py`, `patch_pt.py`, `patch_ru.py`, `patch_r18.py`, `patch_xk.py`, `patch_mo.py`, `patch_lu.py`, `patch_li.py`, `patch_mx.py`, `patch_mn.py`, `patch_mt.py`, `patch_np.py`, `patch_en_nr.py`, `patch_dv.py`, `patch_az.py`, `patch_ar.py`, `patch_en_nz.py`, `patch_nb.py`, `patch_mk.py`, `patch_pa.py`, `patch_py.py` | The same for the Vietnamese, Spanish, Catalan, English, German, Colombian, Salvadoran, Brazilian, Russian, Kosovar, Macanese, Luxembourg, Liechtenstein, Mexican, Mongolian, Maltese, Nepalese, Nauruan, Maldivian, Azerbaijani, Omani, New Zealand, Norwegian, Macedonian, Panamanian and Paraguayan blind spots and a round on currencies, found by other runs; this run's copy carries them all. Of them, the Spanish, Colombian, Salvadoran and Mexican date forms ("hasta el día 31 de diciembre de 2020", "1o. de enero", "a más tardar el 31 de diciembre de 2020") also serve Peruvian Spanish, and so does Paraguay's reading of "no pudo realizarse" (below) |
| `patch_pe.py` | The three fixes below, made for this repository |
| `apply_patches.py` | Applies every patch above once, in order (`patch_py.py`, then `patch_pe.py` last), recording each in `.kit_patches.json` beside the scripts so that none runs twice (`python -X utf8 apply_patches.py <scripts dir>`) |
| `redo.py` | Runs the patches, then again only the scans and detectors the fixes change, the model review of lapsed time limits, references to deleted provisions and empty periods, and the build (`python -X utf8 redo.py <run folder> [--keep-reviews] [--full]`; `--full` runs every step again through `run.sh`; `EMBED_FONTS` names the script that embeds the chart's fonts). It applies the patches through the `apply_patches.py` beside it; only `--full` runs the duplicate-numbering search again |

The model review needs `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` and `LLM_AUTH` set for an OpenAI-compatible Responses API.
It was run as `bash run_triage.sh '^(data/|tools/|README|REPRODUCE|LICENSE|jurisdiction\.json)|/README\.md$'`. Of the 50
flags in the categories it reviews, 49 were reviewed; the model service's content filter refused the request for the
reference in Article 181-B of the Criminal Code (aggravated forms of sexual offences), which was checked by hand (see
EDGE-CASES). Every lapsed time limit is in a law text, so the two reviews of that category drew the same 29 flags;
`build_vulns.py` keeps the later review of each flag (the first found three candidate defects that survived the rebuttal,
the second none).

Changes made for this repository:

- `add_root.py`: this repository marks its laws `Kind: law`, its decrees `Kind: decree` and the oldest available text of
  each act `Kind: publisher`, all already counted as law, and the one change made by a court, ruling STC 918/2021 of the
  Constitutional Court (which restored the earlier text of three articles of the Constitution), `Kind: court`. `court` was
  added to the kinds that count as law: 370 commits. The 8 `Kind: correction` commits (Lexifina's corrections of earlier
  versions) and the documentation are left out.
- `patch_pe.py`, references to repealed placeholders: "sin efecto" (deprived of effect) counts as a repeal marker, so
  Article 757 of the Code of Civil Procedure, "Trámite de la apelación sin efecto suspensivo" (procedure for an appeal
  without suspensive effect), was read as a repealed placeholder, and Articles 783, 799 and 810, which cite it, as
  references to a repealed provision. "sin efecto" followed by "suspensivo" is now ordinary text: 3 flags became 0.
- `patch_pe.py`, references to deleted provisions: a reference that ends its line was taken for a heading and dropped,
  so item 4 of Article 549 of the Civil Code ("... en el caso del artículo 580.") was not read. It is now kept when a
  word and a lower-case "artículo(s)" come before it in the sentence: 16 flags became 17.
- `patch_pe.py`, dead currencies: the sol de oro, Peru's currency until the inti replaced it in 1985, is now read as
  dead in Peru only ("soles de oro", "soles oro"; today's sol is live). No flag: the two amounts in soles oro are written
  in words.
- `patch_py.py` (Paraguay's) had not reached the kit when this run was made; it was added to `apply_patches.py` before
  `patch_pe.py`, and `detectors/notes_scan.py` and `detectors/currency_scan.py` were run again before the build. Its
  reading of "no pudo realizarse" removed the flag on Article 174 of the Code of Civil Procedure ("la defensa que no pudo
  realizar", the defence the party could not make): 16 publisher notes became 15, none in law texts.
- `flags_chart.py` is the kit's later copy, which takes a `tip1` from `config.json`, the tooltip for a category with one
  flag ("1 alerta", not "1 alertas"), and drops the second legend entry when every flag is in law texts.
- `config.json` counts as not law `data/`, `tools/` and the top-level files (`README`, `REPRODUCE.md`, `LICENSE`,
  `jurisdiction.json`), and each act's `README.md` (its list of provisions) wherever it is. Every act folder is law:
  the Constitution, the codes, the laws and the decrees. It gives the chart a shorter Spanish label for references to
  deleted provisions, as Mexico's does.
- `pins.json` already named the language (`es`); Spanish month names were already in the time-limit search.
