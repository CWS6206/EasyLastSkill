---
name: easy-last-skill
description: Deutschsprachige Recherche-Skill fuer aktuelle Themen, Personen, Produkte, Firmen, Repositories, Forschung und Trends in einem frei waehlbaren Zeitraum, standardmaessig in den letzten 30 Tagen. Nutze diese Skill, wenn ein Nutzer nach "letzte 30 Tage", "aktuell", "neueste Reaktionen", "was sagt die Community", "Trend", "Vergleich", "HTML-Bericht" oder einer schnellen deutschsprachigen Lageeinschaetzung mit Quellen fragt.
---

# EasyLastSkill

## Zweck

EasyLastSkill erstellt deutschsprachige Kurzberichte zu aktuellen Themen. Die Skill sammelt oeffentliche Signale aus News, Hacker News, GitHub, Reddit RSS, arXiv, YouTube und optional Bluesky, bewertet sie mit einem einfachen Relevanzscore und verdichtet sie zu einer Lageeinschaetzung mit Quellen.

## Schnellstart

Fuehre das gebuendelte Skript aus dem Skill-Verzeichnis aus:

```bash
python skills/easy-last-skill/scripts/easy_last_skill.py "OpenAI Codex" --tage 30
```

Wenn die Skill aus einem installierten Skill-Ordner geladen wurde, verwende den Pfad relativ zu diesem Ordner:

```bash
python scripts/easy_last_skill.py "OpenAI Codex" --tage 30
```

## Arbeitsablauf

1. Klaere Thema, Zeitraum und gewuenschtes Format. Ohne Nutzerangabe gilt `--tage 30` und `--format markdown`.
2. Nutze bei Vergleichen `--vergleich` oder ein Thema mit `vs`, `versus` oder `gegen`.
3. Nutze `--profil auto`, ausser der Nutzer nennt explizit Person, Firma, Produkt, Repository oder Forschung.
4. Starte das Skript mit dem exakten Suchthema in Anfuehrungszeichen.
5. Lies die Ausgabe vollstaendig: Kurzfazit, Signale, Unsicherheiten und Quellen.
6. Antworte ausschliesslich auf Deutsch.
7. Erfinde keine Treffer, Bewertungen, Kennzahlen oder Quellen. Wenn Quellen fehlen oder Netzwerkzugriff scheitert, sage das transparent.

## Wichtige Befehle

```bash
python scripts/easy_last_skill.py "OpenAI Codex" --tage 30
python scripts/easy_last_skill.py "Codex vs Claude Code" --vergleich
python scripts/easy_last_skill.py "EasyLastSkill" --profil repository --quelle github
python scripts/easy_last_skill.py "Retrieval Augmented Generation" --profil forschung --format html --speichern rag.html
python scripts/easy_last_skill.py --config easy-last-skill.toml
```

## Skriptoptionen

- `--tage N`: Zeitraum rueckwaerts ab heute, Standard `30`.
- `--max-treffer N`: maximale Trefferzahl pro Quelle, Standard `10`.
- `--quelle news|hn|github|reddit|arxiv|youtube|bluesky`: Quelle einschraenken. Mehrfach verwendbar.
- `--profil auto|person|firma|produkt|repository|forschung`: Suchprofil steuern.
- `--vergleich`: Vergleichsmodus aktivieren.
- `--format markdown|html|json`: Ausgabeformat waehlen.
- `--json`: Kurzform fuer `--format json`.
- `--config PFAD`: Konfigurationsdatei lesen.
- `--speichern PFAD`: Bericht in eine Datei schreiben.

## Ausgabeformat

Nutze in der Antwort dieses Muster:

```markdown
EasyLastSkill - Recherche der letzten {TAGE} Tage

Kurzfazit:
{2-4 Saetze zur Lage}

Wichtigste Signale:
1. {Signal mit Quelle und Relevanz}
2. {Signal mit Quelle und Relevanz}
3. {Signal mit Quelle und Relevanz}

Einordnung:
{kurze deutsche Bewertung mit Unsicherheiten}

Quellen:
- {Titel} - {URL}
```

Bei sehr wenigen Treffern erlaeutere zuerst die geringe Datenlage. Bei Vergleichen strukturiere nach Entitaeten und nenne, welche Seite in den gefundenen Signalen staerker vertreten war.

## Konfiguration

Eine lokale `easy-last-skill.toml` kann Standardwerte setzen:

```toml
thema = "OpenAI Codex"
tage = 30
max_treffer = 10
quellen = ["news", "hn", "github", "reddit", "arxiv", "youtube"]
profil = "auto"
format = "markdown"
speicherort = "easy-last-skill-bericht.md"
```

## Quellen und Grenzen

Die Skill nutzt oeffentliche Endpunkte und benoetigt keine API-Schluessel. Je nach Netzwerk, Rate Limits oder Suchbegriff koennen einzelne Quellen leer bleiben. Keine privaten Daten lesen. Keine Logins, Cookies oder Browserprofile auswerten. Keine Aktionen auf Plattformen ausfuehren.
