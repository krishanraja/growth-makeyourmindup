"""Threads text limit: Krish added personal Threads to scope on 27 Oct 2026."""
import unittest

from engine.packs import problems


class ThreadsTextLimitTests(unittest.TestCase):
    def test_threads_text_limit_is_500(self):
        at_limit = 'a' * 499 + '.'
        over_limit = 'a' * 500 + '.'
        self.assertEqual(problems({'platform': 'threads', 'text': at_limit}), [])
        self.assertIn('exceeds the platform text limit',
                      problems({'platform': 'threads', 'text': over_limit}))
        # The same length stays legal where the limit is wider.
        self.assertNotIn('exceeds the platform text limit',
                         problems({'platform': 'linkedin', 'text': over_limit}))


if __name__ == '__main__':
    unittest.main()
