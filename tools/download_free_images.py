#!/usr/bin/env python3
"""
Download stock images into transyes/assets/images based on SEARCH_KEYWORDS.md.

Features:
- Parses markdown asset entries such as: ### `zh/about/team-brand.jpg` `P1` OK
- Skips assets marked OK by default
- Skips files that already exist by default
- Tries primary keywords first, then alternates
- Downloads with polite rate limiting
- Saves files directly to the target relative path under assets/images
- Uses only Python standard library

Providers:
- Pixabay HTML search scraping
- Wikimedia Commons API fallback

Usage examples:
  python transyes/tools/download_free_images.py --dry-run --limit 10
  python transyes/tools/download_free_images.py --only-p1 --delay 2.5
  python transyes/tools/download_free_images.py --include-ok --overwrite
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 TransyesImageBot/1.0"
)

PROJECT_ROOT = Path(
    r"C:\Users\LENOVO\xwechat_files\wxid_q4f3oqwnbin722_2664\msg\file\2026-03\Transyes20240204\transyes"
)


def build_ssl_context(verify_ssl: bool) -> ssl.SSLContext:
    if verify_ssl:
        return ssl.create_default_context()
    return ssl._create_unverified_context()  # type: ignore[attr-defined]


@dataclass
class AssetEntry:
    rel_path: str
    markers: List[str] = field(default_factory=list)
    primary: List[str] = field(default_factory=list)
    alternate: List[str] = field(default_factory=list)
    photo_keywords: List[str] = field(default_factory=list)
    icon_keywords: List[str] = field(default_factory=list)

    @property
    def is_ok(self) -> bool:
        return any(marker.upper() == "OK" for marker in self.markers)

    @property
    def is_p1(self) -> bool:
        return any(marker.upper() == "P1" for marker in self.markers)

    @property
    def is_icon_like(self) -> bool:
        return self.rel_path.startswith("icons/")

    def keyword_batches(self) -> List[List[str]]:
        batches: List[List[str]] = []
        if self.primary:
            batches.append(self.primary)
        if self.alternate:
            batches.append(self.alternate)
        if self.photo_keywords:
            batches.append(self.photo_keywords)
        if self.icon_keywords:
            batches.append(self.icon_keywords)
        if not batches:
            batches.append([self.fallback_query()])
        return [batch for batch in batches if batch]

    def fallback_query(self) -> str:
        stem = Path(self.rel_path).stem
        parts = [part for part in re.split(r"[-_/]+", self.rel_path) if part]
        if self.is_icon_like:
            parts.append("icon")
        path_hint = " ".join(parts[:-1]).replace(".jpg", "").replace(".png", "").replace(".svg", "")
        return f"{stem.replace('-', ' ')} {path_hint}".strip()


def fetch_text(
    url: str,
    timeout: float = 20.0,
    verify_ssl: bool = True,
    retries: int = 2,
) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_error: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(
                request,
                timeout=timeout,
                context=build_ssl_context(verify_ssl),
            ) as response:
                raw = response.read()
            return raw.decode("utf-8", errors="ignore")
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(1.2 + attempt)
    assert last_error is not None
    raise last_error


def fetch_bytes(
    url: str,
    timeout: float = 30.0,
    verify_ssl: bool = True,
    retries: int = 2,
) -> Tuple[bytes, str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Referer": "https://pixabay.com/",
        },
    )
    last_error: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(
                request,
                timeout=timeout,
                context=build_ssl_context(verify_ssl),
            ) as response:
                content_type = response.headers.get_content_type() or ""
                final_url = response.geturl()
                return response.read(), content_type, final_url
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(1.2 + attempt)
    assert last_error is not None
    raise last_error


def parse_markdown(markdown_path: Path) -> List[AssetEntry]:
    lines = markdown_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    entries: List[AssetEntry] = []
    current: Optional[AssetEntry] = None
    current_mode: Optional[str] = None

    heading_re = re.compile(r"^###\s+`([^`]+)`(.*)$")
    marker_re = re.compile(r"`([^`]+)`")

    for raw_line in lines:
        line = raw_line.rstrip()
        heading_match = heading_re.match(line)
        if heading_match:
            if current:
                entries.append(current)
            rel_path = heading_match.group(1).strip()
            markers = marker_re.findall(heading_match.group(2))
            current = AssetEntry(rel_path=rel_path, markers=markers)
            current_mode = None
            continue

        if current is None:
            continue

        stripped = line.strip()
        lower = stripped.lower()
        if stripped.startswith("- Primary:"):
            current_mode = "primary"
            continue
        if stripped.startswith("- Alternate:"):
            current_mode = "alternate"
            continue
        if lower.startswith("- photo keywords:"):
            current_mode = "photo_keywords"
            continue
        if lower.startswith("- icon keywords:"):
            current_mode = "icon_keywords"
            continue
        if stripped.startswith("- Why first:"):
            current_mode = None
            continue

        if current_mode and re.match(r"^\s*-\s+`?.+`?\s*$", line):
            value = re.sub(r"^\s*-\s+", "", line).strip().strip("`")
            getattr(current, current_mode).append(value)

    if current:
        entries.append(current)
    return entries


def dedupe_keep_order(items: Iterable[str]) -> List[str]:
    seen = set()
    output = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def extract_pixabay_candidates(html: str) -> List[str]:
    candidates: List[str] = []

    for srcset in re.findall(r'srcset="([^"]+)"', html):
        for item in srcset.split(","):
            url = item.strip().split(" ")[0].strip()
            if url.startswith("http") and "pixabay" in url:
                candidates.append(url)

    for attr in ("data-lazy-src", "data-lazy", "src"):
        pattern = rf'{attr}="([^"]+)"'
        for url in re.findall(pattern, html):
            if not url.startswith("http"):
                continue
            if "pixabay" not in url:
                continue
            if any(bad in url for bad in (".svg", "/static/", "avatar", "logo")):
                continue
            candidates.append(url)

    upgraded = []
    for url in candidates:
        new_url = url
        new_url = re.sub(r"__\d+", "_1280", new_url)
        new_url = new_url.replace("_340", "_1280").replace("_640", "_1280")
        upgraded.append(new_url)

    return dedupe_keep_order(upgraded)


def search_pixabay(query: str, *, timeout: float, verify_ssl: bool, retries: int) -> List[str]:
    slug = urllib.parse.quote(query.strip().replace(" ", "-"))
    url = f"https://pixabay.com/images/search/{slug}/"
    html = fetch_text(url, timeout=timeout, verify_ssl=verify_ssl, retries=retries)
    return extract_pixabay_candidates(html)


def search_wikimedia(query: str, *, timeout: float, verify_ssl: bool, retries: int) -> List[str]:
    params = {
        "action": "query",
        "generator": "search",
        "gsrnamespace": "6",
        "gsrlimit": "10",
        "gsrsearch": query,
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": "1600",
        "format": "json",
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    data = json.loads(fetch_text(url, timeout=timeout, verify_ssl=verify_ssl, retries=retries))
    pages = data.get("query", {}).get("pages", {})
    results = []
    for page in pages.values():
        for info in page.get("imageinfo", []):
            image_url = info.get("thumburl") or info.get("url")
            if image_url:
                results.append(image_url)
    return dedupe_keep_order(results)


def looks_like_valid_image(data: bytes) -> bool:
    if len(data) < 10_000:
        return False
    signatures = [
        b"\xff\xd8\xff",
        b"\x89PNG\r\n\x1a\n",
        b"RIFF",
    ]
    return any(data.startswith(sig) for sig in signatures)


def is_image_content_type(content_type: str) -> bool:
    return bool(content_type) and content_type.startswith("image/")


def download_to_path(
    url: str,
    output_path: Path,
    *,
    timeout: float = 30.0,
    verify_ssl: bool = True,
    retries: int = 2,
) -> bool:
    data, content_type, final_url = fetch_bytes(
        url,
        timeout=timeout,
        verify_ssl=verify_ssl,
        retries=retries,
    )
    if not is_image_content_type(content_type):
        raise ValueError(f"non-image response: {content_type or 'unknown'} from {final_url}")
    if not looks_like_valid_image(data):
        raise ValueError(f"image signature validation failed for {final_url}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    return True


def sleep_politely(base_delay: float) -> None:
    jitter = random.uniform(0.2, 0.8)
    time.sleep(base_delay + jitter)


def should_skip(entry: AssetEntry, target: Path, args: argparse.Namespace) -> Optional[str]:
    if entry.is_ok and not args.include_ok:
        return "marked OK"
    if target.exists() and not args.overwrite:
        return "file exists"
    if args.only_p1 and not entry.is_p1:
        return "not P1"
    return None


def process_entry(
    entry: AssetEntry,
    image_root: Path,
    args: argparse.Namespace,
) -> dict:
    target = image_root / Path(entry.rel_path)
    skip_reason = should_skip(entry, target, args)
    if skip_reason:
        return {"path": entry.rel_path, "status": "skipped", "reason": skip_reason}

    keyword_batches = entry.keyword_batches()
    if not keyword_batches:
        return {"path": entry.rel_path, "status": "failed", "reason": "no keywords"}

    if args.dry_run:
        return {
            "path": entry.rel_path,
            "status": "planned",
            "queries": [batch[0] for batch in keyword_batches if batch],
        }

    providers = [provider.strip() for provider in args.providers.split(",") if provider.strip()]

    for batch in keyword_batches:
        for query in batch:
            for provider in providers:
                try:
                    if provider == "pixabay":
                        urls = search_pixabay(
                            query,
                            timeout=args.timeout,
                            verify_ssl=args.verify_ssl,
                            retries=args.retries,
                        )
                    elif provider == "wikimedia":
                        urls = search_wikimedia(
                            query,
                            timeout=args.timeout,
                            verify_ssl=args.verify_ssl,
                            retries=args.retries,
                        )
                    else:
                        continue
                except Exception as exc:  # noqa: BLE001
                    print(f"[warn] provider={provider} query={query!r} failed: {exc}")
                    sleep_politely(args.delay)
                    continue

                for url in urls[: args.candidate_limit]:
                    try:
                        if download_to_path(
                            url,
                            target,
                            timeout=args.timeout,
                            verify_ssl=args.verify_ssl,
                            retries=args.retries,
                        ):
                            return {
                                "path": entry.rel_path,
                                "status": "downloaded",
                                "provider": provider,
                                "query": query,
                                "url": url,
                            }
                    except Exception as exc:  # noqa: BLE001
                        print(f"[warn] download failed for {url}: {exc}")

                sleep_politely(args.delay)

    return {"path": entry.rel_path, "status": "failed", "reason": "no usable image found"}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download free stock images for Transyes.")
    parser.add_argument(
        "--keywords-file",
        default=r"C:\Users\LENOVO\xwechat_files\wxid_q4f3oqwnbin722_2664\msg\file\2026-03\Transyes20240204\transyes\assets\images\SEARCH_KEYWORDS.md",
        help="Path to SEARCH_KEYWORDS.md",
    )
    parser.add_argument(
        "--image-root",
        default=r"C:\Users\LENOVO\xwechat_files\wxid_q4f3oqwnbin722_2664\msg\file\2026-03\Transyes20240204\transyes\assets\images",
        help="Root folder where images are stored",
    )
    parser.add_argument(
        "--providers",
        default="pixabay,wikimedia",
        help="Comma-separated providers: pixabay,wikimedia",
    )
    parser.add_argument("--delay", type=float, default=2.5, help="Base delay between remote requests")
    parser.add_argument("--timeout", type=float, default=30.0, help="Request timeout in seconds")
    parser.add_argument("--retries", type=int, default=2, help="Retries per request")
    parser.add_argument("--candidate-limit", type=int, default=5, help="Max URLs to try per query")
    parser.add_argument("--limit", type=int, default=0, help="Process only first N eligible assets")
    parser.add_argument("--only-p1", action="store_true", help="Only process entries marked P1")
    parser.add_argument("--include-ok", action="store_true", help="Include entries marked OK")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    parser.add_argument("--dry-run", action="store_true", help="Parse and report without downloading")
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        help="Disable SSL certificate verification for this run",
    )
    parser.add_argument(
        "--report",
        default=str(PROJECT_ROOT / "assets" / "images" / "download_report.json"),
        help="Where to write the JSON report",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    args.verify_ssl = not args.no_verify_ssl

    keywords_file = Path(args.keywords_file)
    image_root = Path(args.image_root)
    report_path = Path(args.report)

    if not keywords_file.exists():
        print(f"[error] Keywords file not found: {keywords_file}")
        return 1

    entries = parse_markdown(keywords_file)
    if not entries:
        print("[error] No asset entries parsed from markdown.")
        return 1

    results = []
    eligible_count = 0

    for entry in entries:
        target = image_root / Path(entry.rel_path)
        if should_skip(entry, target, args) is None:
            eligible_count += 1

    processed = 0
    for entry in entries:
        target = image_root / Path(entry.rel_path)
        if should_skip(entry, target, args) is not None:
            result = process_entry(entry, image_root, args)
            results.append(result)
            continue

        if args.limit and processed >= args.limit:
            results.append({"path": entry.rel_path, "status": "skipped", "reason": "limit reached"})
            continue

        processed += 1
        print(f"[info] ({processed}/{eligible_count}) {entry.rel_path}")
        result = process_entry(entry, image_root, args)
        print(f"[info] -> {result['status']}")
        results.append(result)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    downloaded = sum(1 for item in results if item["status"] == "downloaded")
    failed = sum(1 for item in results if item["status"] == "failed")
    planned = sum(1 for item in results if item["status"] == "planned")
    skipped = sum(1 for item in results if item["status"] == "skipped")

    print(
        f"[done] downloaded={downloaded} failed={failed} planned={planned} "
        f"skipped={skipped} report={report_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
