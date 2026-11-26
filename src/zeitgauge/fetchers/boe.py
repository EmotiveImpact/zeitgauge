"""Bank of England Interactive Statistical Database (IADB).

CSV download, one row per date, dates like "31 Oct 2026".
Bank Rate is IUMABEDR (monthly average). Check any other series code on the
IADB site before relying on it: the code for the 10-year gilt yield in
config/regions/uk.toml is marked as needing verification.

The Bank asks automated users to identify themselves, so requests carry a
User-Agent string.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime

from . import Series, get_text

URL = ("https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"
       "?csv.x=yes&Datefrom=01/Jan/{start}&Dateto=now&SeriesCodes={code}"
       "&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N")


def _iso(d: str) -> str:
    for fmt in ("%d %b %Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(d.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return d.strip()


def parse_boe(text: str) -> Series:
    reader = csv.reader(io.StringIO(text.strip()))
    header = next(reader, None)
    if not header or len(header) < 2:
        return []
    out = []
    for row in reader:
        if len(row) < 2 or not row[1].strip():
            continue
        try:
            out.append((_iso(row[0]), float(row[1])))
        except ValueError:
            continue
    out.sort(key=lambda t: t[0])
    return out


def fetch_boe(code: str, start_year: int = 2015) -> Series:
    return parse_boe(get_text(URL.format(start=start_year, code=code)))
