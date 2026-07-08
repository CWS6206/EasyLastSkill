# EasyLastSkill

EasyLastSkill ist eine deutschsprachige Codex-/Agent-Skill fuer schnelle Recherchen zu den letzten Tagen eines Themas. Standardmaessig betrachtet sie die letzten 30 Tage und erstellt einen kompakten Bericht mit Quellen.

Autor: Dr. René Bäder PhDs)  
Lizenz: GNU General Public License v3.0

## Installation

Dieses Repository kann als Skill-Quelle genutzt oder lokal mit einem Agent-Skills-kompatiblen Werkzeug installiert werden.

```bash
npx skills add CWS6206/EasyLastSkill -g
```

## Verwendung

```bash
python skills/easy-last-skill/scripts/easy_last_skill.py "OpenAI Codex" --tage 30
```

Optional kann der Bericht gespeichert werden:

```bash
python skills/easy-last-skill/scripts/easy_last_skill.py "OpenAI Codex" --speichern bericht.md
```

## Quellen

Die erste Version nutzt oeffentliche, schluessellose Quellen:

- Google News RSS fuer Nachrichten- und Websignale
- Hacker News Algolia API fuer technische Community-Signale
- GitHub Search API fuer Repository-, Issue- und Diskussionssignale

Alle Ausgaben sind deutsch formuliert. Wenn Netzwerkzugriff, Rate Limits oder Suchbegriffe keine brauchbaren Treffer liefern, weist die Ausgabe darauf hin.

## Lizenz

Dieses Projekt steht unter der GNU General Public License v3.0. Siehe [LICENSE](LICENSE).
