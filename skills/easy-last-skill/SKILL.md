---
name: easy-last-skill
description: Deutschsprachige Recherche-Skill fuer aktuelle Themen, Personen, Produkte, Firmen, Repositories und Trends in einem frei waehlbaren Zeitraum, standardmaessig in den letzten 30 Tagen. Nutze diese Skill, wenn ein Nutzer nach "letzte 30 Tage", "aktuell", "neueste Reaktionen", "was sagt die Community", "Trend", "Vergleich" oder einer schnellen deutschsprachigen Lageeinschaetzung mit Quellen fragt.
---

# EasyLastSkill

## Zweck

EasyLastSkill erstellt deutschsprachige Kurzberichte zu aktuellen Themen. Die Skill sammelt oeffentliche Signale aus Web-/News-RSS, Hacker News und GitHub, begrenzt sie auf einen Zeitraum und verdichtet die Treffer zu einer knappen Lageeinschaetzung mit Quellen.

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

1. Klaere das Thema und den Zeitraum. Ohne Nutzerangabe gilt `--tage 30`.
2. Starte das Skript mit dem exakten Suchthema in Anfuehrungszeichen.
3. Lies die Ausgabe vollstaendig: zuerst Treffer und Abdeckung, dann die Quellenliste.
4. Antworte ausschliesslich auf Deutsch.
5. Erfinde keine Treffer, Bewertungen, Kennzahlen oder Quellen. Wenn Quellen fehlen oder Netzwerkzugriff scheitert, sage das transparent.

## Ausgabeformat

Nutze in der Antwort dieses Muster:

```markdown
EasyLastSkill - Recherche der letzten {TAGE} Tage

Kurzfazit:
{2-4 Saetze zur Lage}

Wichtigste Signale:
1. {Signal mit Quelle}
2. {Signal mit Quelle}
3. {Signal mit Quelle}

Einordnung:
{kurze deutsche Bewertung mit Unsicherheiten}

Quellen:
- {Titel} - {URL}
```

Bei sehr wenigen Treffern erlaeutere zuerst die geringe Datenlage. Bei Vergleichen strukturiere nach Entitaeten und nenne, welche Seite in den gefundenen Signalen staerker vertreten war.

## Skriptoptionen

- `--tage N`: Zeitraum rueckwaerts ab heute, Standard `30`.
- `--max-treffer N`: maximale Trefferzahl pro Quelle, Standard `10`.
- `--quelle news|hn|github`: Quelle einschraenken. Mehrfach verwendbar.
- `--json`: Rohdaten als JSON ausgeben.
- `--speichern PFAD`: Markdown-Bericht in eine Datei schreiben.

## Quellen und Grenzen

Die Skill nutzt oeffentliche Endpunkte und benoetigt keine API-Schluessel. Je nach Netzwerk, Rate Limits oder Suchbegriff koennen einzelne Quellen leer bleiben. Google-News-RSS liefert Nachrichten und Websignale, Hacker News liefert technische Community-Signale, GitHub liefert Repository- und Issue-Signale.

Keine privaten Daten lesen. Keine Logins, Cookies oder Browserprofile auswerten. Keine Aktionen auf Plattformen ausfuehren.
