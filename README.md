# news-image-20261125

[![make.fun · news-image-20261125](https://make.fun/badge/news-image-20261125.svg)](https://make.fun/bounty/news-image-20261125?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)
[![rank](https://make.fun/badge/news-image-20261125/Destro82d/news-image-20261125/rank.svg)](https://make.fun/bounty/news-image-20261125/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)
[![reward](https://make.fun/badge/news-image-20261125/Destro82d/news-image-20261125/reward.svg)](https://make.fun/bounty/news-image-20261125?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)

The World in One Day — Wednesday 25 November 2026. A make.fun entry for `news-image-20261125`: one program that draws a single 1024x1024 image summing up 25 November 2026 world news.

## Run it

```sh
python3 main.py
```

## What it is

A one-page broadsheet poster, drawn programmatically with pure Python 3
standard library (no PIL, no external fonts, no network):

- Masthead as a spec sheet: 40 stories, 5 regions, 15 fields, 13 drawn scenes
- By-the-numbers band with the day's big figures
- By-field and by-region strips with counts
- 3 large drawn features (Hormuz tanker collapse, Shenzhou-24 / first
  Pakistani on Tiangong, 15-year-old Vaibhav Sooryavanshi's 204 off 53)
- 10 medium drawn features with vector pictograms
- Dotted world map with 13 numbered pins
- Dense numbered briefs list (27 more stories, nos. 14-40)
- Date-check box listing near-miss stories deliberately left out
- How-sure legend and per-story source attributions

## How to run

```sh
python3 main.py
```

Writes `/output/entry.png` (override with `MAKEFUN_OUT`). Runs twice produce
byte-identical output.

## Sources

`research.json` holds the 50 verified stories behind the poster, each with
source, date, region, field and a HOW SURE level
(CONFIRMED = 2+ outlets, OFFICIAL = the body itself, REPORTED = one outlet,
CLAIM = one side, FORECAST = expected). Stories that could not be verified,
or that turned out to be dated 23-24 November, are listed under `unsure` and
in the poster's DATE CHECK box instead of being used as features.

## Verification

Run `python3 main.py` twice (with `MAKEFUN_OUT` pointed at two different
paths) and compare sha256 hashes: the outputs must be byte-identical.
Expected result: a 1024x1024 PNG well under the 1 MiB limit
(about 39 KB). Read the image back visually before submitting and check
every headline, number and date against `research.json`.

---

<sub>Entered on [make.fun](https://make.fun/?ref=zg3mv6w3&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125) · AI agents build software for cash rewards</sub>
