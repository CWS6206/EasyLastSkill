# EasyLastSkill

EasyLastSkill ist eine deutschsprachige Codex-/Agent-Skill fuer schnelle Recherchen zu den letzten Tagen eines Themas. Standardmaessig betrachtet sie die letzten 30 Tage und erstellt einen kompakten Bericht mit Quellen, Relevanzscore und Unsicherheiten.

Autor: Dr. René Bäder PhDs  
Lizenz: GNU General Public License v3.0

## Installation

Dieses Repository kann als Skill-Quelle genutzt oder lokal mit einem Agent-Skills-kompatiblen Werkzeug installiert werden.

```bash
npx skills add CWS6206/EasyLastSkill -g
```

Alternativ kann ein `.skill`-Bundle gebaut werden:

```bash
python skills/easy-last-skill/scripts/build_skill_bundle.py
```

## Verwendung

```bash
python skills/easy-last-skill/scripts/easy_last_skill.py "OpenAI Codex" --tage 30
```

Bericht speichern:

```bash
python skills/easy-last-skill/scripts/easy_last_skill.py "OpenAI Codex" --speichern bericht.md
```

HTML-Bericht erzeugen:

```bash
python skills/easy-last-skill/scripts/easy_last_skill.py "OpenAI Codex" --format html --speichern bericht.html
```

Vergleich auswerten:

```bash
python skills/easy-last-skill/scripts/easy_last_skill.py "Codex vs Claude Code" --vergleich
```

## Erweiterungen in Version 0.2

1. Verbesserte deutsche Synthese mit Kurzfazit, neuen Signalen, Einordnung und Unsicherheiten.
2. Mehr Quellen: News, Hacker News, GitHub, Reddit RSS, arXiv, YouTube-Signale und optional Bluesky.
3. Vergleichsmodus fuer `A vs B`, `A versus B` und `A gegen B`.
4. Themenprofile fuer Personen, Firmen, Produkte, Repositories und Forschung.
5. HTML-Export fuer teilbare Berichte.
6. Konfigurationsdatei `easy-last-skill.toml`.
7. Relevanzscore aus Aktualitaet, Quellengewicht, Engagement und Themenuebereinstimmung.
8. Einfacher Bundle-Build fuer Installations- und Release-Prozesse.

## Konfiguration

Siehe [easy-last-skill.example.toml](easy-last-skill.example.toml).

```toml
thema = "OpenAI Codex"
tage = 30
max_treffer = 10
quellen = ["news", "hn", "github", "reddit", "arxiv", "youtube"]
profil = "auto"
format = "markdown"
speicherort = "easy-last-skill-bericht.md"
```

## Quellen

Die Skill nutzt oeffentliche, schluessellose Quellen:

- Google News RSS fuer Nachrichten- und Websignale
- Hacker News Algolia API fuer technische Community-Signale
- GitHub Search API fuer Repository-Signale
- Reddit RSS fuer oeffentliche Community-Signale
- arXiv API fuer Forschungsthemen
- YouTube-Signale ueber oeffentliche RSS-Suche
- Bluesky ueber die oeffentliche Such-API, wenn die API aus der Laufumgebung erreichbar ist

Alle Ausgaben sind deutsch formuliert. Wenn Netzwerkzugriff, Rate Limits oder Suchbegriffe keine brauchbaren Treffer liefern, weist die Ausgabe darauf hin.

## Lizenz

Dieses Projekt steht unter der GNU General Public License v3.0. Siehe [LICENSE](LICENSE).
