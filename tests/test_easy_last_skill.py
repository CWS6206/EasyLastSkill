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
        output = els.render_markdown("Testthema", 30, [], [])
        self.assertIn("keine belastbaren", output)
        self.assertIn("Testthema", output)

    def test_render_markdown_with_sources(self):
        result = els.Treffer(
            quelle="GitHub",
            titel="CWS6206/EasyLastSkill",
            url="https://github.com/CWS6206/EasyLastSkill",
            datum="2026-07-08",
            zusammenfassung="Beispiel",
            score=1,
        )
        output = els.render_markdown("EasyLastSkill", 30, [result], [])
        self.assertIn("1x GitHub", output)
        self.assertIn("CWS6206/EasyLastSkill", output)


if __name__ == "__main__":
    unittest.main()
