#!/usr/bin/env python3
"""Fetch the SCF summary extract files and build the analysis file.

For every survey year 1989-2025 this script needs the Federal Reserve's
Summary Extract Public Data (Stata version, scfpYYYYs.zip). It also needs the
Fed's variable-definition file (bulletin.macro.txt), from which it pulls the
EDCL and KIDS definitions so they can be checked before anything is computed.

Each file is downloaded into data/raw/ unless it is already there. If the
download fails (for example, the network blocks federalreserve.gov), download
the files by hand from the Fed's site, put them in data/raw/, and rerun:

    python get_data.py            # try downloads, then use whatever is in data/raw
    python get_data.py --offline  # only use files already in data/raw

Outputs (only written when every input file is present and passes checks):
    data/processed/scfp_selected.csv       one row per household implicate
    data/processed/definitions_excerpt.txt EDCL and KIDS code from the macro file
    data/processed/variable_labels.csv     Stata labels for the variables kept
"""

import argparse
import io
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

YEARS = list(range(1989, 2026, 3))  # 1989, 1992, ..., 2025
BASE_URL = "https://www.federalreserve.gov/econres/files/"
MACRO_FILE = "bulletin.macro.txt"
KEEP = ["yy1", "y1", "wgt", "networth", "edcl", "kids"]
SOURCE_COLUMNS = KEEP + ["xx1", "x1"]  # 1989 uses the X-prefixed identifiers
DEFINED_VARS = ["EDCL", "KIDS"]

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"


def extract_name(year):
    return f"scfp{year}s.zip"


def year_page(year):
    return f"https://www.federalreserve.gov/econres/scf_{year}.htm"


def download(name):
    """Download BASE_URL/name into data/raw/. Return True on success."""
    dest = RAW / name
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(BASE_URL + name, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as out:
            out.write(resp.read())
    except Exception as exc:  # network policy, 404, timeout...
        tmp.unlink(missing_ok=True)
        print(f"  could not download {BASE_URL + name}: {exc}")
        return False
    tmp.replace(dest)
    print(f"  downloaded {name}")
    return True


def find_extract(year):
    """Locate the summary extract for a year in data/raw/, allowing the
    Stata zip, its unzipped .dta, or the CSV version."""
    exact = RAW / extract_name(year)
    if exact.exists():
        return exact
    for pattern in (f"scfp{year}*.zip", f"scfp{year}*.dta", f"scfp{year}*.csv"):
        hits = sorted(RAW.glob(pattern))
        if hits:
            return hits[0]
    return None


def find_macro():
    exact = RAW / MACRO_FILE
    if exact.exists():
        return exact
    hits = sorted(RAW.glob("*macro*.txt"))
    return hits[0] if hits else None


def definition_blocks(text, var):
    """Return each statement in the SAS macro that assigns to `var`, with a
    few lines of context so conditional (IF/ELSE) logic is visible."""
    lines = text.splitlines()
    pattern = re.compile(rf"\b{var}\s*=", re.IGNORECASE)
    blocks = []
    for i, line in enumerate(lines):
        if pattern.search(line):
            lo, hi = max(0, i - 6), min(len(lines), i + 8)
            blocks.append((i + 1, "\n".join(lines[lo:hi])))
    return blocks


def write_definitions(macro_path):
    text = macro_path.read_text(errors="replace")
    out = [f"Source: {macro_path.name}\n"]
    ok = True
    for var in DEFINED_VARS:
        blocks = definition_blocks(text, var)
        out.append(f"{'=' * 70}\n{var}: {len(blocks)} assignment(s) found\n{'=' * 70}")
        if not blocks:
            ok = False
        for lineno, block in blocks:
            out.append(f"--- line {lineno} ---\n{block}\n")
    PROCESSED.mkdir(parents=True, exist_ok=True)
    path = PROCESSED / "definitions_excerpt.txt"
    path.write_text("\n".join(out))
    print(f"  wrote {path.relative_to(ROOT)}")
    return ok


def read_extract(path):
    """Read one summary extract and return (data, variable labels)."""
    labels = {}
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as zf:
            members = zf.namelist()
            dta = [m for m in members if m.lower().endswith(".dta")]
            csv = [m for m in members if m.lower().endswith(".csv")]
            if not (dta or csv):
                raise ValueError(f"{path.name} has no .dta or .csv inside: {members}")
            member = (dta or csv)[0]
            raw = io.BytesIO(zf.read(member))
            kind = "dta" if dta else "csv"
    else:
        raw, kind = path, path.suffix.lstrip(".")

    if kind == "dta":
        with pd.io.stata.StataReader(raw) as reader:
            df = reader.read()
            labels = reader.variable_labels()
    else:
        df = pd.read_csv(raw, usecols=lambda c: c.lower() in SOURCE_COLUMNS)

    df.columns = [c.lower() for c in df.columns]
    labels = {k.lower(): v for k, v in labels.items()}
    # The 1989 extract uses X1/XX1 where later public extracts use Y1/YY1.
    # Both represent replicate-specific ID and stable family ID, respectively.
    if "y1" not in df.columns and "x1" in df.columns:
        df = df.rename(columns={"x1": "y1"})
        labels["y1"] = labels.get("x1", "")
    if "yy1" not in df.columns and "xx1" in df.columns:
        df = df.rename(columns={"xx1": "yy1"})
        labels["yy1"] = labels.get("xx1", "")
    missing = [c for c in KEEP if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name} lacks variables {missing}")
    return df[KEEP], {k: labels.get(k, "") for k in KEEP}


def check(df, year):
    """Sanity checks that would catch a wrong file or a changed coding."""
    implicate = df["y1"] - 10 * df["yy1"]
    if not implicate.between(1, 5).all():
        raise ValueError(f"{year}: Y1 is not YY1*10 + implicate(1-5)")
    if not (df.groupby("yy1").size() == 5).all():
        raise ValueError(f"{year}: some households do not have exactly 5 implicates")
    if not set(df["edcl"].unique()) <= {1, 2, 3, 4}:
        raise ValueError(f"{year}: unexpected EDCL codes {sorted(df['edcl'].unique())}")
    if (df["kids"] < 0).any():
        raise ValueError(f"{year}: negative KIDS values")
    if (df["wgt"] <= 0).any():
        raise ValueError(f"{year}: non-positive weights")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--offline", action="store_true",
                        help="do not try to download; use files in data/raw only")
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)

    # 1. Variable definitions come first: nothing is built without them.
    print("Variable definitions")
    macro = find_macro()
    if macro is None and not args.offline and download(MACRO_FILE):
        macro = RAW / MACRO_FILE

    # 2. One summary extract per survey year.
    print("Summary extracts")
    extracts = {}
    for year in YEARS:
        path = find_extract(year)
        if path is None and not args.offline and download(extract_name(year)):
            path = RAW / extract_name(year)
        extracts[year] = path

    missing = [(MACRO_FILE, "the 'Variable Definitions (TXT)' link on any year page, e.g. "
                + year_page(2022))] if macro is None else []
    missing += [(extract_name(y), "'Summary Extract Public Data', Stata version, on "
                 + year_page(y)) for y, p in extracts.items() if p is None]
    if missing:
        print(f"\nMissing {len(missing)} file(s). Download each from the official "
              f"Fed page and save it in {RAW.relative_to(ROOT)}/ under this name:")
        for name, where in missing:
            print(f"  {name:22s} <- {BASE_URL + name}\n  {'':22s}    (listed as {where})")
        print("Then rerun: python get_data.py --offline")
        sys.exit(1)

    if not write_definitions(macro):
        sys.exit(f"Could not find assignments for {DEFINED_VARS} in {macro.name}; "
                 "check that it is the Fed's variable-definition macro.")

    frames, label_rows = [], []
    for year, path in extracts.items():
        df, labels = read_extract(path)
        check(df, year)
        df.insert(0, "year", year)
        frames.append(df)
        label_rows += [{"year": year, "variable": k, "label": v} for k, v in labels.items()]
        print(f"  {year}: {df['yy1'].nunique():,} households from {path.name}")

    out = pd.concat(frames, ignore_index=True)
    out.to_csv(PROCESSED / "scfp_selected.csv", index=False)
    pd.DataFrame(label_rows).to_csv(PROCESSED / "variable_labels.csv", index=False)
    print(f"  wrote {(PROCESSED / 'scfp_selected.csv').relative_to(ROOT)}")
    print("\nRead data/processed/definitions_excerpt.txt and variable_labels.csv "
          "before running plot.py (see README).")


if __name__ == "__main__":
    main()
