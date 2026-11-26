# Third-party repositories

Zeitgauge is MIT-licensed. Other people's code is kept out of this repository. `scripts/get_third_party.sh` clones each project, pinned to the exact commit reviewed on 26 November 2026, into `third_party/`, which git ignores. This keeps licences clean and lets you study or run the projects beside Zeitgauge.

Each entry gives what the project is, its licence, and how Zeitgauge uses it.

---

## Use as a dependency

**flack0x/trendspyg** (MIT)
- What: Google Trends downloader that can stand in for pytrends.
- Use: an optional dependency (`pip install "zeitgauge[trends]"`), wrapped by `fetchers/trends.py`. It covers the culture channel and the playbook trend checks.

## Study and borrow ideas (licence allows copying with attribution)

**AndrewFSee/macro-regime-nowcaster** (MIT)
- What: a dynamic factor model, Kalman filter and Markov-switching regime model across 75 FRED series, with a Streamlit dashboard.
- Use: the blueprint for Zeitgauge version 2. Once enough history is stored, a fitted factor model can replace hand-set weights and a regime model can replace the fixed four-quadrant cut-offs. It is US-only, so the UK needs its own series list.

**alochemes/nowcast-quad** (MIT)
- What: a weekly US growth and inflation nowcaster, plotted on a four-quadrant map, that runs unattended and alerts you when it stops.
- Use: a model for the scheduled pipeline, especially its "tell me when it breaks" design. Its growth-by-inflation quadrant is a useful second clock beside ours.

**amazon-science/nowcasting-recession-risk** (Apache 2.0)
- What: a monthly recession-risk nowcast for the US and Euro Area, combining macro and financial conditions.
- Use: a method to adapt for a UK recession probability. Apache 2.0 allows reuse with notice, and requires noting any changes.

**Seshat-Global-History-Databank/seshat_api** (MIT code)
- What: a Python client for the Seshat historical databank.
- Use: background research on long-run societal cycles, for Turchin-style work.
- Licence warning: the data it downloads is CC BY-NC-SA, which is non-commercial only.

**Seshat-Global-History-Databank/build_polaris_dataset** (MIT code)
- What: builds the Polaris dataset from Seshat.
- Use and licence: the same as above. Research only.

## Reference only (licence prevents or is unclear for copying)

**Joe-Wait/onspy** (GPL-3.0)
- What: an ONS API client with parquet syncing and MCP tools.
- Use: run it separately if helpful. Do not copy its code into Zeitgauge, because GPL would then apply to the whole project. `fetchers/ons.py` is an independent, much smaller client.

**Asterbons/Cliodynamics** (no licence file)
- What: a Political Stress Index pipeline for Germany built from federal statistics.
- Use: read it to see how a real PSI is built from official data. It shaped the design of `indicators/psi.py`. No code was copied. Without a licence the default is "all rights reserved".

**RichardScottOZ/Cliodynamics** (no licence)
- What: notes and code around Turchin and Korotayev's 2020 review of the 2010 structural-demographic forecast.
- Use: reading only.

---

## Why a clone script and not git submodules

Submodules would put these projects into every clone of Zeitgauge, including the GPL and unlicensed ones. A script keeps them optional and local. The pinned commits mean everyone studies the same version.
