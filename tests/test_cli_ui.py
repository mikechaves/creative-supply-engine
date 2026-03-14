import unittest

from src.cli_ui import render_pulse_header


class CliUiTests(unittest.TestCase):
    def test_header_contains_pulse_and_no_color_disables_ansi(self) -> None:
        header = render_pulse_header(no_color=True, term_width=120)
        self.assertIn("PULSE", header)
        self.assertNotIn("\x1b[", header)


if __name__ == "__main__":
    unittest.main()
