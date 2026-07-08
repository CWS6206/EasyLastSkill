#!/usr/bin/env python3
"""Deutschsprachige Recherche der letzten Tage ohne externe Abhaengigkeiten."""

from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Iterable


VERSION = "0.2.0"
USER_AGENT = f"EasyLastSkill/{VERSION} (+https://github.com/CWS6206/EasyLastSkill)"
DEFAULT_SOURCES = ("news", "hn", "github", "reddit", "arxiv", "youtube", "bluesky")
DEFAULT_ACTIVE_SOURCES = ("news", "hn", "github", "reddit", "arxiv", "youtube")
SOURCE_LABELS = {
    "news": "News",
    "hn": "Hacker News",
    "github": "GitHub",
    "reddit": "Reddit",
    "arxiv": "arXiv",
    "youtube": "YouTube",
    "bluesky": "Bluesky",
}
PROFILE_SOURCES = {
    "auto": DEFAULT_ACTIVE_SOURCES,
    "person": ("news", "github", "reddit", "youtube", "hn"),
    "firma": ("news", "github", "reddit", "youtube", "hn"),
    "produkt": ("news", "reddit", "hn", "github", "youtube"),
    "repository": ("github", "hn", "reddit", "news", "youtube"),
    "forschung": ("arxiv", "news", "hn", "github"),
}
CONFIG_NAME = "easy-last-skill.toml"


@dataclass(frozen=True)
class Treffer:
    quelle: str
    titel: str
    url: str
    datum: str
    zusammenfassung: str = ""
    score: int = 0
    relevanz: int = 0


@dataclass(frozen=True)
class Recherche:
    thema: str
    tage: int
    profil: str
    quellen: tuple[str, ...]
    treffer: list[Treffer]
    warnungen: list[str]


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
    text = re.sub(r"<[^>]+>", " ", text)
    text = " ".join(text.replace("\n", " ").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def parse_simple_toml(path: Path) -> dict[str, object]:
    config: dict[str, object] = {}
    if not path.exists():
        return config
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or "=" not in line:
            continue
        key, raw_value = [part.strip() for part in line.split("=", 1)]
        if raw_value.startswith("[") and raw_value.endswith("]"):
            values = []
            for value in raw_value[1:-1].split(","):
                value = value.strip().strip('"').strip("'")
                if value:
                    values.append(value)
            config[key] = values
        elif raw_value.startswith(('"', "'")) and raw_value.endswith(('"', "'")):
            config[key] = raw_value[1:-1]
        elif raw_value.isdigit():
            config[key] = int(raw_value)
        elif raw_value.lower() in {"true", "false"}:
            config[key] = raw_value.lower() == "true"
        else:
            config[key] = raw_value
    return config


def in_window(value: str | None, start: dt.datetime) -> bool:
    parsed = parse_date(value)
    return parsed is not None and parsed >= start


def tokens(value: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[\w-]{3,}", value, flags=re.UNICODE)}


def detect_profile(topic: str) -> str:
    lowered = topic.lower()
    if re.search(r"^[\w.-]+/[\w.-]+$", topic):
        return "repository"
    if any(word in lowered for word in ("paper", "studie", "research", "forschung", "modell", "llm")):
        return "forschung"
    if any(word in lowered for word in ("gmbh", "ag", "inc", "ltd", "corp", "company", "firma")):
        return "firma"
    if any(word in lowered for word in ("app", "tool", "produkt", "software", "plattform")):
        return "produkt"
    if len(topic.split()) in {2, 3} and all(part[:1].isupper() for part in topic.split()):
        return "person"
    return "produkt"


def profile_query(topic: str, profile: str) -> str:
    additions = {
        "person": "",
        "firma": " company product release funding hiring",
        "produkt": " review release alternative issue",
        "repository": " GitHub release issue pull request",
        "forschung": " research paper arxiv benchmark",
        "auto": "",
    }
    return f"{topic}{additions.get(profile, '')}".strip()


def split_comparison(topic: str) -> list[str]:
    parts = re.split(r"\s+(?:vs\.?|versus|gegen)\s+", topic, flags=re.IGNORECASE)
    cleaned = [part.strip(" \"'") for part in parts if part.strip(" \"'")]
    return cleaned if len(cleaned) >= 2 else []


def search_google_news(topic: str, days: int, max_results: int, label: str) -> list[Treffer]:
    start = utc_now() - dt.timedelta(days=days)
    query = urllib.parse.quote_plus(f"{topic} when:{days}d")
    url = f"https://news.google.com/rss/search?q={query}&hl=de&gl=DE&ceid=DE:de"
    root = ET.fromstring(fetch_text(url))
    results: list[Treffer] = []
    for item in root.findall("./channel/item"):
        published = item.findtext("pubDate")
        if not in_window(published, start):
            continue
        parsed = parse_date(published)
        results.append(
            Treffer(
                quelle=label,
                titel=clean_text(item.findtext("title"), 180),
                url=clean_text(item.findtext("link"), 500),
                datum=parsed.date().isoformat() if parsed else "",
                zusammenfassung=clean_text(item.findtext("description")),
            )
        )
        if len(results) >= max_results:
            break
    return results


def search_news(topic: str, days: int, max_results: int) -> list[Treffer]:
    return search_google_news(topic, days, max_results, "News")


def search_youtube(topic: str, days: int, max_results: int) -> list[Treffer]:
    return search_google_news(f"site:youtube.com {topic}", days, max_results, "YouTube")


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
        points = int(hit.get("points") or 0)
        comments = int(hit.get("num_comments") or 0)
        created = parse_date(hit.get("created_at"))
        link = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        results.append(
            Treffer(
                quelle="Hacker News",
                titel=clean_text(hit.get("title") or hit.get("story_title"), 180),
                url=link,
                datum=created.date().isoformat() if created else "",
                zusammenfassung=f"{points} Punkte, {comments} Kommentare",
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


def search_reddit(topic: str, days: int, max_results: int) -> list[Treffer]:
    start = utc_now() - dt.timedelta(days=days)
    query = urllib.parse.quote_plus(topic)
    url = f"https://www.reddit.com/search.rss?q={query}&sort=new&t=month"
    root = ET.fromstring(fetch_text(url))
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    results: list[Treffer] = []
    for entry in root.findall("atom:entry", ns):
        updated = entry.findtext("atom:updated", namespaces=ns)
        if not in_window(updated, start):
            continue
        link = ""
        for candidate in entry.findall("atom:link", ns):
            if candidate.attrib.get("href"):
                link = candidate.attrib["href"]
                break
        parsed = parse_date(updated)
        results.append(
            Treffer(
                quelle="Reddit",
                titel=clean_text(entry.findtext("atom:title", namespaces=ns), 180),
                url=link,
                datum=parsed.date().isoformat() if parsed else "",
                zusammenfassung=clean_text(entry.findtext("atom:content", namespaces=ns)),
            )
        )
        if len(results) >= max_results:
            break
    return results


def search_arxiv(topic: str, days: int, max_results: int) -> list[Treffer]:
    start = utc_now() - dt.timedelta(days=days)
    query = urllib.parse.quote_plus(f'all:"{topic}"')
    url = (
        "https://export.arxiv.org/api/query?"
        f"search_query={query}&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"
    )
    root = ET.fromstring(fetch_text(url))
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    results: list[Treffer] = []
    for entry in root.findall("atom:entry", ns):
        published = entry.findtext("atom:published", namespaces=ns)
        if not in_window(published, start):
            continue
        parsed = parse_date(published)
        results.append(
            Treffer(
                quelle="arXiv",
                titel=clean_text(entry.findtext("atom:title", namespaces=ns), 180),
                url=clean_text(entry.findtext("atom:id", namespaces=ns), 500),
                datum=parsed.date().isoformat() if parsed else "",
                zusammenfassung=clean_text(entry.findtext("atom:summary", namespaces=ns)),
            )
        )
        if len(results) >= max_results:
            break
    return results


def search_bluesky(topic: str, days: int, max_results: int) -> list[Treffer]:
    since = (utc_now() - dt.timedelta(days=days)).isoformat().replace("+00:00", "Z")
    query = urllib.parse.quote_plus(topic)
    url = (
        "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?"
        f"q={query}&sort=latest&since={urllib.parse.quote_plus(since)}&limit={max_results}"
    )
    data = fetch_json(url)
    results: list[Treffer] = []
    for post in data.get("posts", [])[:max_results]:
        record = post.get("record", {})
        created = parse_date(record.get("createdAt") or post.get("indexedAt"))
        author = post.get("author", {}).get("handle", "unbekannt")
        likes = int(post.get("likeCount") or 0)
        reposts = int(post.get("repostCount") or 0)
        replies = int(post.get("replyCount") or 0)
        uri = post.get("uri", "")
        post_id = uri.rsplit("/", 1)[-1] if uri else ""
        link = f"https://bsky.app/profile/{author}/post/{post_id}" if post_id else f"https://bsky.app/profile/{author}"
        text = clean_text(record.get("text"), 220)
        title = clean_text(f"@{author}: {text}", 180)
        results.append(
            Treffer(
                quelle="Bluesky",
                titel=title,
                url=link,
                datum=created.date().isoformat() if created else "",
                zusammenfassung=f"{likes} Likes, {reposts} Reposts, {replies} Antworten",
                score=likes + reposts + replies,
            )
        )
    return results


def score_result(result: Treffer, topic: str) -> Treffer:
    topic_tokens = tokens(topic)
    haystack = tokens(f"{result.titel} {result.zusammenfassung}")
    overlap = len(topic_tokens & haystack)
    recency = 0
    parsed = parse_date(result.datum)
    if parsed:
        age = max((utc_now().date() - parsed.date()).days, 0)
        recency = max(0, 30 - age)
    source_weight = {
        "News": 18,
        "Hacker News": 16,
        "GitHub": 14,
        "Reddit": 15,
        "arXiv": 17,
        "YouTube": 15,
        "Bluesky": 15,
    }.get(result.quelle, 10)
    engagement = min(result.score // 10, 25)
    relevance = source_weight + recency + (overlap * 12) + engagement
    return replace(result, relevanz=relevance)


def collect(topic: str, days: int, max_results: int, sources: Iterable[str], profile: str) -> Recherche:
    handlers = {
        "news": search_news,
        "hn": search_hn,
        "github": search_github,
        "reddit": search_reddit,
        "arxiv": search_arxiv,
        "youtube": search_youtube,
        "bluesky": search_bluesky,
    }
    all_results: list[Treffer] = []
    warnings: list[str] = []
    query = profile_query(topic, profile)
    for source in sources:
        handler = handlers[source]
        try:
            all_results.extend(handler(query, days, max_results))
        except (urllib.error.URLError, TimeoutError, ET.ParseError, json.JSONDecodeError) as exc:
            warnings.append(f"{source}: {exc}")
    scored = [score_result(result, topic) for result in dedupe(all_results)]
    scored.sort(key=lambda item: (item.relevanz, item.datum, item.score), reverse=True)
    return Recherche(thema=topic, tage=days, profil=profile, quellen=tuple(sources), treffer=scored, warnungen=warnings)


def dedupe(results: list[Treffer]) -> list[Treffer]:
    seen: set[str] = set()
    unique: list[Treffer] = []
    for result in results:
        key = result.url or result.titel.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(result)
    return unique


def source_counts(results: list[Treffer]) -> str:
    counts: dict[str, int] = {}
    for result in results:
        counts[result.quelle] = counts.get(result.quelle, 0) + 1
    return ", ".join(f"{count}x {source}" for source, count in sorted(counts.items()))


def render_markdown(research: Recherche) -> str:
    lines = [
        f"# EasyLastSkill - Recherche der letzten {research.tage} Tage",
        "",
        f"**Thema:** {research.thema}",
        f"**Profil:** {research.profil}",
        f"**Erstellt:** {utc_now().date().isoformat()}",
        "",
    ]
    if research.warnungen:
        lines.extend(["## Hinweise", ""])
        lines.extend(f"- {warning}" for warning in research.warnungen)
        lines.append("")
    if not research.treffer:
        lines.extend(
            [
                "## Kurzfazit",
                "",
                "Es wurden keine belastbaren oeffentlichen Treffer im angegebenen Zeitraum gefunden.",
                "",
            ]
        )
        return "\n".join(lines)

    top = research.treffer[:3]
    lines.extend(
        [
            "## Kurzfazit",
            "",
            f"Gefunden wurden {len(research.treffer)} Signale aus {source_counts(research.treffer)}. "
            f"Die staerksten Hinweise kommen aktuell von {', '.join(sorted({item.quelle for item in top}))}. "
            "Die Einordnung bleibt quellenbasiert und vermeidet Spekulation.",
            "",
            "## Was ist neu?",
            "",
        ]
    )
    for result in top:
        lines.append(f"- {result.titel} ({result.quelle}, {result.datum}, Relevanz {result.relevanz})")
    lines.extend(["", "## Wichtigste Signale", ""])
    for index, result in enumerate(research.treffer[:10], start=1):
        suffix = f" - {result.zusammenfassung}" if result.zusammenfassung else ""
        lines.append(
            f"{index}. **{result.titel}** ({result.quelle}, {result.datum}, Relevanz {result.relevanz}){suffix}"
        )
    lines.extend(
        [
            "",
            "## Community- und Quellen-Signal",
            "",
            quality_sentence(research),
            "",
            "## Unsicherheiten",
            "",
            uncertainty_sentence(research),
            "",
            "## Quellen",
            "",
        ]
    )
    for result in research.treffer[:20]:
        lines.append(f"- {result.titel} - {result.url}")
    return "\n".join(lines)


def render_comparison_markdown(researches: list[Recherche]) -> str:
    days = researches[0].tage if researches else 30
    lines = [
        f"# EasyLastSkill - Vergleich der letzten {days} Tage",
        "",
        f"**Erstellt:** {utc_now().date().isoformat()}",
        "",
        "## Kurzfazit",
        "",
    ]
    ranked = sorted(researches, key=lambda item: sum(result.relevanz for result in item.treffer), reverse=True)
    if ranked and ranked[0].treffer:
        lines.append(
            f"Das staerkste gefundene Momentum hat **{ranked[0].thema}** mit "
            f"{len(ranked[0].treffer)} Treffern und einer Relevanzsumme von "
            f"{sum(result.relevanz for result in ranked[0].treffer)}."
        )
    else:
        lines.append("Fuer den Vergleich wurden keine belastbaren oeffentlichen Treffer gefunden.")
    lines.extend(["", "## Vergleichstabelle", ""])
    lines.append("| Thema | Treffer | Top-Quelle | Relevanzsumme | Staerkstes Signal |")
    lines.append("|---|---:|---|---:|---|")
    for research in researches:
        top_source = research.treffer[0].quelle if research.treffer else "-"
        top_title = research.treffer[0].titel if research.treffer else "-"
        total = sum(result.relevanz for result in research.treffer)
        lines.append(f"| {research.thema} | {len(research.treffer)} | {top_source} | {total} | {top_title} |")
    for research in researches:
        lines.extend(["", f"## {research.thema}", ""])
        if not research.treffer:
            lines.append("Keine belastbaren Treffer im Zeitraum.")
            continue
        for result in research.treffer[:5]:
            lines.append(f"- **{result.titel}** ({result.quelle}, Relevanz {result.relevanz}) - {result.url}")
    return "\n".join(lines)


def quality_sentence(research: Recherche) -> str:
    sources = {result.quelle for result in research.treffer}
    if len(sources) >= 3:
        return "Die Datenlage ist breit genug fuer eine vorsichtige Einordnung, weil mehrere Quellentypen Treffer geliefert haben."
    if len(sources) == 2:
        return "Die Datenlage ist brauchbar, aber noch nicht breit; zwei Quellentypen bestaetigen das Thema."
    return "Die Datenlage ist schmal; die Treffer sollten als Hinweis, nicht als abschliessende Bewertung gelesen werden."


def uncertainty_sentence(research: Recherche) -> str:
    if research.warnungen:
        return "Einzelne Quellen konnten nicht abgefragt werden. Dadurch kann das Bild unvollstaendig sein."
    if len(research.treffer) < 3:
        return "Es gibt nur wenige Treffer. Eine klare Trendaussage waere zu stark."
    return "Die Relevanzwerte sind heuristisch und ersetzen keine manuelle Quellenpruefung."


def markdown_to_html(markdown: str, title: str) -> str:
    body: list[str] = []
    in_list = False
    for line in markdown.splitlines():
        if line.startswith("- "):
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f"<li>{html.escape(line[2:])}</li>")
            continue
        if in_list:
            body.append("</ul>")
            in_list = False
        if line.startswith("# "):
            body.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            body.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.strip():
            body.append(f"<p>{html.escape(line)}</p>")
    if in_list:
        body.append("</ul>")
    return (
        "<!doctype html>\n<html lang=\"de\">\n<head>\n<meta charset=\"utf-8\">\n"
        f"<title>{html.escape(title)}</title>\n"
        "<style>body{font-family:Segoe UI,Arial,sans-serif;max-width:980px;margin:40px auto;"
        "padding:0 22px;line-height:1.55;color:#1f2937}h1,h2{color:#111827}"
        "h1{border-bottom:3px solid #0f766e;padding-bottom:12px}li{margin:8px 0}"
        "p{margin:10px 0}code{background:#f3f4f6;padding:2px 4px}</style>\n"
        "</head>\n<body>\n"
        + "\n".join(body)
        + "\n</body>\n</html>\n"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deutschsprachige Recherche zu aktuellen Signalen der letzten Tage."
    )
    parser.add_argument("thema", nargs="?", help="Suchthema, Person, Produkt, Firma oder Trend")
    parser.add_argument("--tage", type=int, help="Rueckblickzeitraum in Tagen")
    parser.add_argument("--max-treffer", type=int, help="Maximale Treffer pro Quelle")
    parser.add_argument("--quelle", action="append", choices=DEFAULT_SOURCES, help="Quelle einschraenken")
    parser.add_argument("--profil", choices=tuple(PROFILE_SOURCES), help="Suchprofil")
    parser.add_argument("--vergleich", action="store_true", help="Thema als Vergleich auswerten")
    parser.add_argument("--format", choices=("markdown", "html", "json"), help="Ausgabeformat")
    parser.add_argument("--json", action="store_true", help="Rohdaten als JSON ausgeben")
    parser.add_argument("--config", help=f"Konfigurationsdatei, Standard: ./{CONFIG_NAME}")
    parser.add_argument("--speichern", help="Bericht in Datei schreiben")
    parser.add_argument("--version", action="version", version=f"EasyLastSkill {VERSION}")
    return parser


def merged_options(args: argparse.Namespace) -> argparse.Namespace:
    config_path = Path(args.config or CONFIG_NAME)
    config = parse_simple_toml(config_path)
    args.thema = args.thema or str(config.get("thema", "")).strip()
    args.tage = args.tage or int(config.get("tage", 30))
    args.max_treffer = args.max_treffer or int(config.get("max_treffer", 10))
    args.profil = args.profil or str(config.get("profil", "auto"))
    args.format = "json" if args.json else args.format or str(config.get("format", "markdown"))
    if args.quelle:
        sources = args.quelle
    else:
        sources = config.get("quellen")
        if not isinstance(sources, list):
            sources = None
    args.quelle = sources
    args.speichern = args.speichern or config.get("speicherort")
    return args


def validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if not args.thema:
        parser.error("thema fehlt. Gib ein Thema an oder setze thema in easy-last-skill.toml.")
    if args.tage < 1:
        parser.error("--tage muss mindestens 1 sein")
    if args.max_treffer < 1:
        parser.error("--max-treffer muss mindestens 1 sein")
    if args.profil not in PROFILE_SOURCES:
        parser.error(f"--profil muss eines von {', '.join(PROFILE_SOURCES)} sein")
    invalid_sources = [source for source in (args.quelle or []) if source not in DEFAULT_SOURCES]
    if invalid_sources:
        parser.error(f"Unbekannte Quelle: {', '.join(invalid_sources)}")


def output_payload(researches: list[Recherche], output_format: str, comparison: bool) -> str:
    if output_format == "json":
        payload = {
            "version": VERSION,
            "vergleich": comparison,
            "recherchen": [
                {
                    **{key: value for key, value in asdict(research).items() if key != "treffer"},
                    "treffer": [asdict(result) for result in research.treffer],
                }
                for research in researches
            ],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)
    markdown = render_comparison_markdown(researches) if comparison else render_markdown(researches[0])
    if output_format == "html":
        return markdown_to_html(markdown, "EasyLastSkill Bericht")
    return markdown


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = build_parser()
    args = merged_options(parser.parse_args(argv))
    validate_args(parser, args)

    comparison_topics = split_comparison(args.thema) if args.vergleich or split_comparison(args.thema) else []
    topics = comparison_topics or [args.thema]
    researches: list[Recherche] = []
    for topic in topics:
        profile = detect_profile(topic) if args.profil == "auto" else args.profil
        sources = tuple(args.quelle or PROFILE_SOURCES[profile])
        researches.append(collect(topic, args.tage, args.max_treffer, sources, profile))

    output = output_payload(researches, args.format, comparison=bool(comparison_topics))
    if args.speichern:
        Path(args.speichern).write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
