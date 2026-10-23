# Wealth gap by parents' education, SCF 1989–2025

How has mean net worth differed between families with children whose parent
has a bachelor's degree or more and those whose parent has a high-school
education or less, across the Federal Reserve's Survey of Consumer Finances
(SCF) from 1989 to the 2025 survey?

## Definitions used

| Concept | SCF variable | Rule |
|---|---|---|
| Parent's education | `EDCL`, education of the household **reference person** | 4 = bachelor's or more; 1–2 = high school or less; 3 (some college/associate) excluded |
| Family with children at home | `KIDS` | `KIDS > 0` |
| Wealth | `NETWORTH` | weighted mean, in the constant dollars of the extract release |
| Weight | `WGT` | computed within each of the 5 implicates, then averaged |

The `EDCL` codes have been checked against the Federal Reserve's official
2025 `bulletin.macro.txt` (education-of-reference-person definition). The
macro also defines `KIDS` from the family relationship roster, including
natural, step- and foster children. The download script saves the relevant
macro code to `data/processed/definitions_excerpt.txt` for audit.

## Files

All files come from the Fed's SCF pages (`https://www.federalreserve.gov/econres/scf_YYYY.htm`):

| File | Where on the page | Purpose |
|---|---|---|
| `bulletin.macro.txt` | "SAS macro – Variable Definitions (TXT)" | definitions of `EDCL`, `KIDS`, `NETWORTH` |
| `scfp1989s.zip` … `scfp2025s.zip` (13 files) | "Summary Extract Public Data", Stata version | the data, one file per survey year |

The file names are the official `https://www.federalreserve.gov/econres/files/<name>`
pattern; if a link on a year page differs, save it under the name above.
Download all extracts from the **same (current) release** so every year is in
the same constant dollars.

## POLISCI 158 Section 03 submission

This repository implements Option B: the family-wealth-by-parental-education
reproduction using original Federal Reserve public SCF extracts, not values
traced from an image. The required deliverables are `get_data.py`, `plot.py`,
`figure.png`, and this README. `figure.png` is generated only after the real
data download and plotting steps succeed. The automated GitHub Actions run
is available under **Actions → Reproduce SCF figure**.

**Original source:** https://www.federalreserve.gov/econres/scfindex.htm

**Method:** Keep families with `KIDS > 0`, split by reference-person `EDCL`
(4 versus 1–2), compute weighted mean `NETWORTH` within each implicate using
`WGT`, and average the five implicate estimates by year. Plot group means
as a single academic-journal-style chart, 1989–2025, in constant 2025 dollars.\nThe wealth ratio is retained in the results CSV as an additional statistic.

## Reproduction result

The automated run successfully downloaded all 13 original Federal Reserve
summary extracts (1989–2025), computed the weighted means from those files,
and generated [`figure.png`](figure.png). The underlying estimates are saved
in [`results/mean_networth_by_education.csv`](results/mean_networth_by_education.csv).

In 2025, families with children whose reference person held a bachelor's
degree or more had mean net worth of approximately **$2.29 million**, versus
**$269,180** for families with a high-school education or less: a ratio of
**8.51 to 1**. In 1989, the corresponding ratio was **4.66 to 1**. All amounts
are in 2025 dollars. These are descriptive weighted means, not causal effects
of education, and no uncertainty intervals are shown.

**Style comparison:** The final figure follows the course's recommended academic
journal example: monochrome lines, circle and square markers, a single plot,
labeled axes, and a numbered caption with a source note below. The data trend
and approximate endpoints agree with the example shown in the section guide.
A pixel-by-pixel numerical comparison has not been performed.

## Usage

```
pip install -r requirements.txt
python get_data.py            # downloads into data/raw/, or lists what to fetch by hand
python get_data.py --offline  # after placing files in data/raw/ manually
python plot.py                # results/*.csv and figures/*.png
```

## Limitations

- **Reference person only.** `EDCL` is one person's education. In couples the
  SCF reference person has typically been the man in a mixed-sex couple (or
  the older partner in a same-sex couple), so a more-educated mother does not
  move the family into the college group. Unverified here; check the codebook.
- **`KIDS` definition.** The Federal Reserve macro counts children from
  family relationship codes (including natural, step and foster children).
  This is not identical to a generic under-18-child definition.
- **Education coding changed in 2016** (years of schooling → highest degree).
  `EDCL` is meant to be harmonized, but the break may still shift the groups.
- **Means are tail-driven.** The SCF oversamples very wealthy families; mean
  net worth, and so the gap, is dominated by the top and can jump between
  waves. The lab's later switch to medians addresses this.
- **No standard errors yet.** Proper SCF errors need the replicate weights and
  the multiple-imputation variance; the figure shows point estimates only.
  Group sample sizes are in the results CSV.
- **Composition changes.** The share of parents with a degree has grown since
  1989, so each group's makeup (age, region, family size) shifts over time.
