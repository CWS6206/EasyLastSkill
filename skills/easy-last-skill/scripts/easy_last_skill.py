#!/usr/bin/env python3
"""Deutschsprachige Recherche der letzten Tage ohne externe Abhaengigkeiten."""

from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import html
import json
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from typing import Iterable


USER_AGENT = "EasyLastSkill/0.1 (+https://github.com/CWS6206/EasyLastSkill)"
DEFAULT_SOURCES = ("news", "hn", "github")


@dataclass(frozen=True)
class Treffer:
    quelle: str
    titel: str
    url: str
    datum: str
    zusammenfassung: str = ""
    score: int = 0


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def parse_date(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    value = value.strip()
    for parser in (
        lambda v: dt.datetime.fromisoformat(v.replace("Z", "+00:00")),
        lambda v: email.utils.parsedate_to_datetime(v),
    ):
        try:
            parsed = parser(value)
        except (TypeError, ValueError):
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    return None


def fetch_json(url: str, timeout: int = 20) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_text(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def clean_text(value: str | None, limit: int = 280) -> str:
    text = html.unescape(value or "")
    text = " ".join(text.replace("\n", " ").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def in_window(value: str | None, start: dt.datetime) -> bool:
    parsed = parse_date(value)
    return parsed is not None and parsed >= start


def search_news(topic: str, days: int, max_results: int) -> list[Treffer]:
    start = utc_now() - dt.timedelta(days=days)
    query = urllib.parse.quote_plus(f"{topic} when:{days}d")
    url = (
        "https://news.google.com/rss/search?"
        f"q={query}&hl=de&gl=DE&ceid=DE:de"
    )
    xml_text = fetch_text(url)
    root = ET.fromstring(xml_text)
    results: list[Treffer] = []
    for item in root.findall("./channel/item"):
        published = item.findtext("pubDate")
        if not in_window(published, start):
            continue
        title = clean_text(item.findtext("title"), 180)
        link = clean_text(item.findtext("link"), 500)
        summary = clean_text(item.findtext("description"))
        parsed = parse_date(published)
        results.append(
            Treffer(
                quelle="News",
                titel=title,
                url=link,
                datum=parsed.date().isoformat() if parsed else "",
                zusammenfassung=summary,
            )
        )
        if len(results) >= max_results:
            break
    return results


def search_hn(topic: str, days: int, max_results: int) -> list[Treffer]:
    since = int((utc_now() - dt.timedelta(days=days)).timestamp())
    query = urllib.parse.quote_plus(topic)
    url = (
        "https://hn.algolia.com/api/v1/search_by_date?"
        f"query={query}&tags=story&numericFilters=created_at_i>{since}"
    )
    data = fetch_json(url)
    results: list[Treffer] = []
    for hit in data.get("hits", [])[:max_results]:
        title = clean_text(hit.get("title") or hit.get("story_title"), 180)
        link = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        points = int(hit.get("points") or 0)
        comments = int(hit.get("num_comments") or 0)
        summary = f"{points} Punkte, {comments} Kommentare"
        created = parse_date(hit.get("created_at"))
        results.append(
            Treffer(
                quelle="Hacker News",
                titel=title,
                url=link,
                datum=created.date().isoformat() if created else "",
                zusammenfassung=summary,
                score=points + comments,
            )
        )
    return results


def search_github(topic: str, days: int, max_results: int) -> list[Treffer]:
    start = (utc_now() - dt.timedelta(days=days)).date().isoformat()
    query = urllib.parse.quote_plus(f"{topic} pushed:>={start}")
    url = (
        "https://api.github.com/search/repositories?"
        f"q={query}&sort=updated&order=desc&per_page={max_results}"
    )
    data = fetch_json(url)
    results: list[Treffer] = []
    for item in data.get("items", [])[:max_results]:
        stars = int(item.get("stargazers_count") or 0)
        updated = parse_date(item.get("updated_at"))
        results.append(
            Treffer(
                quelle="GitHub",
                titel=clean_text(item.get("full_name"), 180),
                url=item.get("html_url", ""),
                datum=updated.date().isoformat() if updated else "",
                zusammenfassung=clean_text(item.get("description") or f"{stars} Sterne"),
                score=stars,
            )
        )
    return results


def collect(topic: str, days: int, max_results: int, sources: Iterable[str]) -> tuple[list[Treffer], list[str]]:
    handlers = {
        "news": search_news,
        "hn": search_hn,
        "github": search_github,
    }
    all_results: list[Treffer] = []
    warnings: list[str] = []
    for source in sources:
        handler = handlers[source]
        try:
            all_results.extend(handler(topic, days, max_results))
        except (urllib.error.URLError, TimeoutError, ET.ParseError, json.JSONDecodeError) as exc:
            warnings.append(f"{source}: {exc}")
    all_results.sort(key=lambda item: (item.datum, item.score), reverse=True)
    return all_results, warnings


def render_markdown(topic: str, days: int, results: list[Treffer], warnings: list[str]) -> str:
    lines = [
        f"# EasyLastSkill - Recherche der letzten {days} Tage",
        "",
        f"**Thema:** {topic}",
        f"**Erstellt:** {utc_now().date().isoformat()}",
        "",
    ]
    if warnings:
        lines.extend(["## Hinweise", ""])
        lines.extend(f"- {warning}" for warning in warnings)
        lines.append("")
    if not results:
        lines.extend(
            [
                "## Kurzfazit",
                "",
                "Es wurden keine belastbaren oeffentlichen Treffer im angegebenen Zeitraum gefunden.",
                "",
            ]
        )
        return "\n".join(lines)

    source_counts: dict[str, int] = {}
    for result in results:
        source_counts[result.quelle] = source_counts.get(result.quelle, 0) + 1
    counts = ", ".join(f"{count}x {source}" for source, count in sorted(source_counts.items()))
    lines.extend(
        [
            "## Kurzfazit",
            "",
            f"Gefunden wurden {len(results)} Signale aus {counts}. Die neuesten und staerksten Treffer stehen oben; die Bewertung bleibt quellenbasiert und vermeidet Spekulation.",
            "",
            "## Wichtigste Signale",
            "",
        ]
    )
    for index, result in enumerate(results[:10], start=1):
        suffix = f" - {result.zusammenfassung}" if result.zusammenfassung else ""
        lines.append(f"{index}. **{result.titel}** ({result.quelle}, {result.datum}){suffix}")
    lines.extend(["", "## Quellen", ""])
    for result in results[:20]:
        lines.append(f"- {result.titel} - {result.url}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deutschsprachige Recherche zu aktuellen Signalen der letzten Tage."
    )
    parser.add_argument("thema", help="Suchthema, Person, Produkt, Firma oder Trend")
    parser.add_argument("--tage", type=int, default=30, help="Rueckblickzeitraum in Tagen")
    parser.add_argument("--max-treffer", type=int, default=10, help="Maximale Treffer pro Quelle")
    parser.add_argument("--quelle", action="append", choices=DEFAULT_SOURCES, help="Quelle einschraenken")
    parser.add_argument("--json", action="store_true", help="Rohdaten als JSON ausgeben")
    parser.add_argument("--speichern", help="Markdown-Bericht in Datei schreiben")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.tage < 1:
        parser.error("--tage muss mindestens 1 sein")
    if args.max_treffer < 1:
        parser.error("--max-treffer muss mindestens 1 sein")

    sources = tuple(args.quelle or DEFAULT_SOURCES)
    results, warnings = collect(args.thema, args.tage, args.max_treffer, sources)

    if args.json:
        payload = {
            "thema": args.thema,
            "tage": args.tage,
            "quellen": sources,
            "warnungen": warnings,
            "treffer": [asdict(result) for result in results],
        }
        output = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        output = render_markdown(args.thema, args.tage, results, warnings)

    if args.speichern:
        with open(args.speichern, "w", encoding="utf-8") as handle:
            handle.write(output)
            handle.write("\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
