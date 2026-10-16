"""Unit tests for the LogCapture library.

The listener hooks are driven directly here, which is what lets these tests run
without a Robot context. The level handling has its own tests against a stubbed
``BuiltIn``, because outside a Robot run the real one raises.
"""
import pytest

from LogCapture import DEFAULT_CAPTURE_LEVEL, LogCapture


def message(text, level='INFO'):
    """Build a message dictionary of the shape Robot's listener API passes."""
    return {'message': text, 'level': level, 'timestamp': '20260101 00:00:00.000',
            'html': 'no'}


@pytest.fixture(name='capture')
def capture_fixture():
    """A library instance already capturing, with the log level left alone."""
    library = LogCapture()
    library.start_capturing_log_messages(level='NONE')
    return library


class TestCapturing:
    """Recording the messages a keyword logs."""

    def test_messages_are_recorded_in_order(self, capture):
        """Order matters: a retry sequence reads as one message per attempt."""
        capture.log_message(message('first'))
        capture.log_message(message('second'))

        assert [m['message'] for m in capture.get_captured_log_messages()] == ['first', 'second']

    def test_level_is_recorded(self, capture):
        """The level is the reason to capture at all."""
        capture.log_message(message('a warning', level='WARN'))

        assert capture.get_captured_log_messages()[0]['level'] == 'WARN'

    def test_nothing_is_recorded_before_capturing_starts(self):
        """A library that is merely imported must not collect anything."""
        library = LogCapture()

        library.log_message(message('before'))

        assert library.get_captured_log_messages() == []

    def test_nothing_is_recorded_after_capturing_stops(self, capture):
        """Stopping lets a test log its own diagnostics without recording them."""
        capture.log_message(message('during'))
        capture.stop_capturing_log_messages()

        capture.log_message(message('after'))

        assert [m['message'] for m in capture.get_captured_log_messages()] == ['during']

    def test_starting_again_forgets_the_earlier_messages(self, capture):
        """One phase of a test must not see the previous phase's log."""
        capture.log_message(message('old'))

        capture.start_capturing_log_messages(level='NONE')
        capture.log_message(message('new'))

        assert [m['message'] for m in capture.get_captured_log_messages()] == ['new']

    def test_stop_returns_what_was_captured(self, capture):
        """The convenient form for a test that reads the log once, at the end."""
        capture.log_message(message('only'))

        assert [m['message'] for m in capture.stop_capturing_log_messages()] == ['only']

    def test_the_caller_cannot_disturb_the_recording(self, capture):
        """Copies are returned, so reading cannot corrupt a later assertion."""
        capture.log_message(message('original'))

        capture.get_captured_log_messages()[0]['message'] = 'tampered'

        assert capture.get_captured_log_messages()[0]['message'] == 'original'

    def test_capturing_ends_with_the_test(self, capture):
        """A test that forgets to stop must not keep recording into the next one."""
        capture.end_test('a test', {})

        capture.log_message(message('after the test'))

        assert capture.get_captured_log_messages() == []

    def test_the_end_of_the_test_forgets_what_was_captured(self, capture):
        """The recording goes too: Robot logs a test's own failure as a message."""
        capture.log_message(message('during the test'))

        capture.end_test('a test', {})

        assert capture.get_captured_log_messages() == []


class TestFiltering:
    """Selecting among the captured messages."""

    @pytest.fixture(name='populated')
    def populated_fixture(self, capture):
        """A recording holding the same text at two levels, plus one other."""
        capture.log_message(message('connecting to the database', level='INFO'))
        capture.log_message(message('retrying after a timeout', level='WARN'))
        capture.log_message(message('retrying after a timeout', level='DEBUG'))
        return capture

    def test_unfiltered_returns_everything(self, populated):
        """No filter means the whole recording."""
        assert len(populated.get_captured_log_messages()) == 3

    def test_filter_by_level(self, populated):
        """The same text at two levels is what makes the level filter necessary."""
        assert len(populated.get_captured_log_messages(level='WARN')) == 1

    def test_filter_by_level_is_case_insensitive(self, populated):
        """Robot spells levels in upper case; a test should not have to."""
        assert len(populated.get_captured_log_messages(level='warn')) == 1

    def test_filter_by_pattern(self, populated):
        """A glob selects across levels."""
        matches = populated.get_captured_log_messages(pattern='*timeout*')

        assert len(matches) == 2

    def test_pattern_is_a_glob_not_a_substring(self, populated):
        """Documented behaviour: a partial match needs its own wildcards."""
        assert populated.get_captured_log_messages(pattern='timeout') == []

    def test_pattern_is_case_sensitive(self, populated):
        """Log text is compared as written, unlike the level."""
        assert populated.get_captured_log_messages(pattern='*TIMEOUT*') == []

    def test_both_filters_apply_together(self, populated):
        """Level and pattern narrow the selection, they do not widen it."""
        matches = populated.get_captured_log_messages(level='DEBUG', pattern='*timeout*')

        assert len(matches) == 1
        assert matches[0]['level'] == 'DEBUG'


class TestAssertion:
    """The Captured Log Should Contain keyword."""

    @pytest.fixture(name='populated')
    def populated_fixture(self, capture):
        """A recording with one INFO message and a repeated warning."""
        capture.log_message(message('rotating credentials', level='INFO'))
        capture.log_message(message('retrying', level='WARN'))
        capture.log_message(message('retrying', level='WARN'))
        return capture

    def test_passes_on_a_match(self, populated):
        """The ordinary case."""
        populated.captured_log_should_contain('*credentials*')

    def test_passes_on_a_match_at_the_given_level(self, populated):
        """The level is part of what is asserted, not only the text."""
        populated.captured_log_should_contain('retrying', level='WARN')

    def test_fails_when_nothing_matches(self, populated):
        """An absent log line is a failure, not an empty result."""
        with pytest.raises(AssertionError, match='no captured message matches'):
            populated.captured_log_should_contain('*missing*')

    def test_fails_when_the_level_differs(self, populated):
        """"Logged at the wrong level" has to be distinguishable from "missing"."""
        with pytest.raises(AssertionError, match='at level INFO'):
            populated.captured_log_should_contain('retrying', level='INFO')

    def test_failure_lists_what_was_captured(self, populated):
        """Without the recording in the message the reader has nothing to go on."""
        with pytest.raises(AssertionError, match="INFO 'rotating credentials'"):
            populated.captured_log_should_contain('*missing*')

    def test_failure_says_so_when_nothing_was_captured(self, capture):
        """Forgetting to start capturing is the obvious mistake, so name it."""
        with pytest.raises(AssertionError, match='was capturing started'):
            capture.captured_log_should_contain('*anything*')

    def test_count_passes_on_the_exact_number(self, populated):
        """A retry logs one line per attempt, so the count is the contract."""
        populated.captured_log_should_contain('retrying', count=2)

    def test_count_fails_on_another_number(self, populated):
        """The failure states both numbers."""
        with pytest.raises(AssertionError, match='2 captured messages match, expected 3'):
            populated.captured_log_should_contain('retrying', count=3)

    def test_count_accepts_a_string(self, populated):
        """Robot passes arguments as text unless told otherwise."""
        populated.captured_log_should_contain('retrying', count='2')


class StubBuiltIn:  # pylint: disable=too-few-public-methods
    """Stands in for Robot's BuiltIn, recording the levels it was asked to set."""

    def __init__(self, current='INFO'):
        self.current = current
        self.requested = []

    def set_log_level(self, level):
        """Record the request and answer with the level that was in force."""
        self.requested.append(level)
        previous, self.current = self.current, level
        return previous


class TestLogLevel:
    """Raising the log level while capturing, and putting it back."""

    @pytest.fixture(name='stub')
    def stub_fixture(self, monkeypatch):
        """Replace BuiltIn in the library's namespace with the stub."""
        stub = StubBuiltIn()
        monkeypatch.setattr('LogCapture.BuiltIn', lambda: stub)
        return stub

    def test_capturing_raises_the_level_to_debug(self, stub):
        """Robot filters below the active level before a listener sees anything."""
        LogCapture().start_capturing_log_messages()

        assert stub.requested == [DEFAULT_CAPTURE_LEVEL]

    def test_a_given_level_is_used(self, stub):
        """Capturing at WARN keeps the INFO chatter out of the recording."""
        LogCapture().start_capturing_log_messages(level='WARN')

        assert stub.requested == ['WARN']

    def test_stopping_puts_the_level_back(self, stub):
        """A raised level must not outlive the capture."""
        library = LogCapture()
        library.start_capturing_log_messages()

        library.stop_capturing_log_messages()

        assert stub.requested == [DEFAULT_CAPTURE_LEVEL, 'INFO']

    def test_the_end_of_the_test_puts_the_level_back(self, stub):
        """A failing test cannot leave the rest of the suite logging at DEBUG."""
        library = LogCapture()
        library.start_capturing_log_messages()

        library.end_test('a test', {})

        assert stub.requested == [DEFAULT_CAPTURE_LEVEL, 'INFO']

    def test_the_level_is_restored_only_once(self, stub):
        """Stopping twice must not set the level a second time."""
        library = LogCapture()
        library.start_capturing_log_messages()

        library.stop_capturing_log_messages()
        library.stop_capturing_log_messages()

        assert stub.requested == [DEFAULT_CAPTURE_LEVEL, 'INFO']

    def test_starting_twice_remembers_the_original_level(self, stub):
        """The second start must restore to the suite's level, not to the first."""
        library = LogCapture()

        library.start_capturing_log_messages()
        library.start_capturing_log_messages(level='TRACE')
        library.stop_capturing_log_messages()

        assert stub.requested == [DEFAULT_CAPTURE_LEVEL, 'INFO', 'TRACE', 'INFO']
        assert stub.current == 'INFO'

    def test_none_leaves_the_level_alone(self, stub):
        """For a test asserting what a given log level does and does not write."""
        library = LogCapture()

        library.start_capturing_log_messages(level='NONE')
        library.stop_capturing_log_messages()

        assert stub.requested == []

    def test_none_is_case_insensitive(self, stub):
        """As for the level filter, the caller should not have to shout."""
        LogCapture().start_capturing_log_messages(level='none')

        assert stub.requested == []

    def test_capturing_works_outside_a_robot_run(self):
        """With no Robot context the level cannot be set, and that is not an error."""
        library = LogCapture()

        library.start_capturing_log_messages()
        library.log_message(message('logged with no Robot around'))

        assert len(library.get_captured_log_messages()) == 1
