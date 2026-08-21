"""Unit tests for Markdown to Slack mrkdwn converter."""

import unittest
from src.converter import convert_gfm_to_slack_mrkdwn, split_message_for_slack


class TestConverter(unittest.TestCase):
    def test_convert_bold_and_headers(self):
        input_text = "# Main Title\nThis is **bold text** and __also bold__."
        expected = "*Main Title*\nThis is *bold text* and *also bold*."
        self.assertEqual(convert_gfm_to_slack_mrkdwn(input_text), expected)

    def test_convert_links(self):
        input_text = "Check out [Google](https://google.com) and [Docs](https://example.com/docs)."
        expected = "Check out <https://google.com|Google> and <https://example.com/docs|Docs>."
        self.assertEqual(convert_gfm_to_slack_mrkdwn(input_text), expected)

    def test_convert_table_to_codeblock(self):
        input_text = (
            "Here is a table:\n"
            "| Name | Role |\n"
            "| --- | --- |\n"
            "| Alice | Admin |\n"
            "| Bob | Dev |\n"
            "End of table."
        )
        result = convert_gfm_to_slack_mrkdwn(input_text)
        self.assertIn("```\n| Name | Role |\n| --- | --- |\n| Alice | Admin |\n| Bob | Dev |\n```", result)
        self.assertIn("End of table.", result)

    def test_preserve_fenced_code_blocks(self):
        input_text = (
            "Here is some code:\n"
            "```python\n"
            "# This is not a header\n"
            "def foo():\n"
            "    **not_bold** = [Link](https://example.com)\n"
            "```\n"
            "And outside **is bold**."
        )
        result = convert_gfm_to_slack_mrkdwn(input_text)
        self.assertIn("```python\n# This is not a header\ndef foo():\n    **not_bold** = [Link](https://example.com)\n```", result)
        self.assertIn("And outside *is bold*.", result)

    def test_preserve_inline_code(self):
        input_text = "Run `git commit -m \"**msg**\"` now."
        expected = "Run `git commit -m \"**msg**\"` now."
        self.assertEqual(convert_gfm_to_slack_mrkdwn(input_text), expected)

    def test_split_long_message(self):
        long_text = "\n".join([f"Line {i}: Some detailed description content here" for i in range(100)])
        chunks = split_message_for_slack(long_text, max_length=500)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 600)


if __name__ == "__main__":
    unittest.main()
