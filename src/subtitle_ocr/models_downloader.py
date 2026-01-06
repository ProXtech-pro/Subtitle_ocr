import io
import json
import os
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable, Optional, Tuple


LogFn = Optional[Callable[[str], None]]


def _log(log: LogFn, msg: str) -> None:
    if log:
        log(msg)


def _http_get_json(url: str, log: LogFn = None) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            # GitHub API: set a UA
            "User-Agent": "subtitle-ocr-pro",
            "Accept": "application/vnd.github+json",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    return json.loads(data.decode("utf-8"))


def _http_download(url: str, log: LogFn = None) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "subtitle-ocr-pro"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def download_tessdata_from_github_release(
    owner: str,
    repo: str,
    asset_name: str,
    dest_dir: Path,
    log: LogFn = None,
) -> Tuple[bool, str]:
    """
    Downloads a zip asset from the *latest* GitHub release and extracts traineddata
    files into dest_dir.

    - owner/repo: GitHub repo
    - asset_name: e.g. tessdata_best_min.zip
    - dest_dir: e.g. ./tessdata_best
    """
    dest_dir = dest_dir.resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)

    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    _log(log, f"GitHub API: {api_url}")

    try:
        release = _http_get_json(api_url, log=log)
    except Exception as e:
        return False, f"Failed to query latest release: {type(e).__name__}: {e}"

    assets = release.get("assets", [])
    if not assets:
        return False, "No assets found in latest release."

    asset = None
    for a in assets:
        if a.get("name") == asset_name:
            asset = a
            break

    if not asset:
        available = ", ".join([a.get("name", "?") for a in assets])
        return False, f"Asset not found: {asset_name}. Available: {available}"

    download_url = asset.get("browser_download_url")
    if not download_url:
        return False, "Asset has no browser_download_url."

    _log(log, f"Downloading asset: {asset_name}")
    _log(log, f"URL: {download_url}")

    try:
        blob = _http_download(download_url, log=log)
    except Exception as e:
        return False, f"Failed to download asset: {type(e).__name__}: {e}"

    # Extract zip in-memory
    try:
        zf = zipfile.ZipFile(io.BytesIO(blob))
    except Exception as e:
        return False, f"Downloaded asset is not a valid zip: {type(e).__name__}: {e}"

    extracted = 0
    for info in zf.infolist():
        name = info.filename.replace("\\", "/")
        if name.endswith("/"):
            continue
        # Accept either root files or nested tessdata_best/
        base = name.split("/")[-1]
        if base.endswith(".traineddata"):
            target = dest_dir / base
            _log(log, f"Extracting: {base} -> {target}")
            with zf.open(info, "r") as src, target.open("wb") as dst:
                dst.write(src.read())
            extracted += 1

    if extracted == 0:
        return False, "Zip contains no .traineddata files."

    return True, f"OK: extracted {extracted} traineddata file(s) to {dest_dir}"
