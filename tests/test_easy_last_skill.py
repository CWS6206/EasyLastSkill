import datetime as dt
import unittest

from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "easy-last-skill" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import easy_last_skill as els  # noqa: E402


class EasyLastSkillTests(unittest.TestCase):
    def test_parse_date_iso_zulu(self):
        parsed = els.parse_date("2026-07-08T10:00:00Z")
        self.assertEqual(parsed, dt.datetime(2026, 7, 8, 10, 0, tzinfo=dt.timezone.utc))

    def test_render_markdown_empty_results(self):
        research = els.Recherche("Testthema", 30, "produkt", ("news",), [], [])
        output = els.render_markdown(research)
        self.assertIn("keine belastbaren", output)
        self.assertIn("Testthema", output)

    def test_render_markdown_with_sources_and_relevance(self):
        result = els.Treffer(
            quelle="GitHub",
            titel="CWS6206/EasyLastSkill",
            url="https://github.com/CWS6206/EasyLastSkill",
            datum="2026-07-08",
            zusammenfassung="Beispiel",
            score=1,
            relevanz=42,
        )
        research = els.Recherche("EasyLastSkill", 30, "repository", ("github",), [result], [])
        output = els.render_markdown(research)
        self.assertIn("1x GitHub", output)
        self.assertIn("Relevanz 42", output)
        self.assertIn("CWS6206/EasyLastSkill", output)

    def test_split_comparison(self):
        self.assertEqual(els.split_comparison("Codex vs Claude Code"), ["Codex", "Claude Code"])
        self.assertEqual(els.split_comparison("Codex gegen Claude Code"), ["Codex", "Claude Code"])

    def test_config_parser(self):
        path = Path(__file__).resolve().parents[1] / ".tmp-test-config.toml"
        path.write_text(
            'tage = 14\nquellen = ["news", "github"]\nformat = "html"\n',
            encoding="utf-8",
        )
        try:
            config = els.parse_simple_toml(path)
        finally:
            path.unlink(missing_ok=True)
        self.assertEqual(config["tage"], 14)
        self.assertEqual(config["quellen"], ["news", "github"])
        self.assertEqual(config["format"], "html")

    def test_html_export_contains_document(self):
        html = els.markdown_to_html("# Titel\n\n## Abschnitt\n\nText", "Titel")
        self.assertIn("<!doctype html>", html)
        self.assertIn("<h1>Titel</h1>", html)


if __name__ == "__main__":
    unittest.main()
