"""Download the official IRCC workbook."""

import urllib.request
from pathlib import Path

from .config import RAW_FILE, SOURCE_URL

XLSX_SIGNATURE = b"PK"  # .xlsx files are ZIP archives


def download_workbook(url: str = SOURCE_URL, dest: Path = RAW_FILE, timeout: int = 60) -> Path:
    """Download the workbook to `dest` and return the path.

    The file is written to a temporary name first, so a failed download never
    leaves a half-written workbook behind.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (immigration-forecast)"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content = response.read()

    if not content.startswith(XLSX_SIGNATURE):
        raise ValueError("Downloaded file is not an .xlsx workbook (missing ZIP signature).")

    tmp = dest.with_suffix(".part")
    tmp.write_bytes(content)
    tmp.replace(dest)
    return dest
