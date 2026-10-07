"""Unit tests for the shared normalisation and mocked-keyword registry."""
import unittest

from _mock_core import (
    MOCKED_KEYWORDS,
    is_keyword_mocked,
    mocked_keyword_key,
    normalize_keyword_name,
    register_mocked_keyword,
    unregister_mocked_keyword,
)


class TestNormalizeKeywordName(unittest.TestCase):
    """Tests for normalize_keyword_name."""

    def test_matches_robot_name_semantics(self):
        """Case, spaces and underscores are all insignificant, as in Robot."""
        canonical = normalize_keyword_name("Fetch Rows")
        for written in ("fetch rows", "FETCH ROWS", "Fetch_Rows", "fetchrows",
                        "  Fetch   Rows  "):
            self.assertEqual(normalize_keyword_name(written), canonical, written)

    def test_distinct_names_stay_distinct(self):
        """Normalisation must not collapse genuinely different names."""
        self.assertNotEqual(normalize_keyword_name("Fetch Rows"),
                            normalize_keyword_name("Fetch Row"))

    def test_accepts_non_string(self):
        """A name arriving as a non-string is coerced rather than raising."""
        self.assertEqual(normalize_keyword_name(123), "123")


class TestMockedKeywordRegistry(unittest.TestCase):
    """Tests for the registry MockCoverage consults."""

    def setUp(self):
        """Start from an empty registry."""
        MOCKED_KEYWORDS.clear()

    def tearDown(self):
        """Leave no state behind for other tests."""
        MOCKED_KEYWORDS.clear()

    def test_register_then_query(self):
        """A registered keyword reads back as mocked."""
        register_mocked_keyword("/tmp/demo.resource", "Fetch Rows")
        source_key = mocked_keyword_key("/tmp/demo.resource", "Fetch Rows")[0]

        self.assertTrue(is_keyword_mocked(source_key, "Fetch Rows"))

    def test_query_is_name_insensitive(self):
        """Lookup uses the same name matching as mocking."""
        register_mocked_keyword("/tmp/demo.resource", "Fetch Rows")
        source_key = mocked_keyword_key("/tmp/demo.resource", "Fetch Rows")[0]

        self.assertTrue(is_keyword_mocked(source_key, "fetch_rows"))

    def test_unregister(self):
        """Resetting a mock makes the keyword countable again."""
        register_mocked_keyword("/tmp/demo.resource", "Fetch Rows")
        unregister_mocked_keyword("/tmp/demo.resource", "Fetch Rows")
        source_key = mocked_keyword_key("/tmp/demo.resource", "Fetch Rows")[0]

        self.assertFalse(is_keyword_mocked(source_key, "Fetch Rows"))

    def test_other_keyword_in_same_resource_is_unaffected(self):
        """Mocking one keyword does not exclude its neighbours from coverage."""
        register_mocked_keyword("/tmp/demo.resource", "Fetch Rows")
        source_key = mocked_keyword_key("/tmp/demo.resource", "Fetch Rows")[0]

        self.assertFalse(is_keyword_mocked(source_key, "Other Keyword"))

    def test_same_name_in_another_resource_is_unaffected(self):
        """Resources sharing a keyword name are tracked independently."""
        register_mocked_keyword("/tmp/a.resource", "Fetch Rows")
        other_key = mocked_keyword_key("/tmp/b.resource", "Fetch Rows")[0]

        self.assertFalse(is_keyword_mocked(other_key, "Fetch Rows"))

    def test_unregister_unknown_is_silent(self):
        """Resetting something never mocked is not an error."""
        unregister_mocked_keyword("/tmp/demo.resource", "Never Mocked")


if __name__ == '__main__':
    unittest.main()
