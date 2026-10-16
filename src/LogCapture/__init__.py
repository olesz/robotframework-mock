"""The messages a keyword logged, so that a test can assert on them.

A keyword's log output is part of its contract: a wrapper that takes a ``${level}``
argument and drops it looks identical from the outside, because the message still
appears - only at the wrong level. Robot writes messages to ``log.html``, which a
test cannot read while it runs, so the only way to see them is to listen for them.

This library registers itself as its own listener and records the messages logged
while it is capturing.

**It raises the log level while capturing, and puts it back afterwards.** Robot
filters messages below the active log level *before* a listener is offered them, so
at the default ``INFO`` a ``DEBUG`` message never arrives - measured: a listener at
``INFO`` sees ``['INFO', 'WARN']`` out of a DEBUG/INFO/WARN sequence. Leaving that
to the caller makes "no message was logged" and "the message was filtered"
indistinguishable, which is exactly the confusion a test is written to avoid.

Capturing ends with the test that started it - the level is put back and the
recording let go - so neither can leak into the next test.

Example:
    | Library | LogCapture |
    |  |  |
    | Start Capturing Log Messages |
    | Rotate Credentials |
    | Captured Log Should Contain | *credentials rotated* | level=WARN |
"""
# pylint: disable=invalid-name
from fnmatch import fnmatchcase
from typing import Dict, List, Optional

from robot.api.deco import keyword
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError

#: Level set while capturing unless the caller asks for another one. Everything
#: Robot logs by default is at or above ``DEBUG``; ``TRACE`` adds argument and
#: return-value lines for every keyword, which is rarely what a test is after.
DEFAULT_CAPTURE_LEVEL = 'DEBUG'

#: Value that tells ``Start Capturing Log Messages`` to leave the level alone.
NO_LEVEL_CHANGE = 'NONE'


class LogCapture:
    """Record the messages logged while capturing, and assert on them."""

    ROBOT_LISTENER_API_VERSION = 2
    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self):
        self.ROBOT_LIBRARY_LISTENER = self
        self._messages: List[Dict[str, str]] = []
        self._capturing = False
        self._restore_level: Optional[str] = None

    # ------------------------------------------------------------------ listener

    def log_message(self, message):
        """Listener hook: Robot calls this for every message a keyword logs."""
        if self._capturing:
            self._messages.append(dict(message))

    def end_test(self, name, attributes):  # pylint: disable=unused-argument
        """Listener hook: end the capture with the test that started it.

        Both the level and the recording are let go. A later test reading the
        recording without starting one of its own must not see the previous
        test's messages - and Robot logs a test's own failure as a message, so
        what leaked would include that failure too.
        """
        self._stop()
        self._messages = []

    # ------------------------------------------------------------------ keywords

    @keyword
    def start_capturing_log_messages(self, level: str = DEFAULT_CAPTURE_LEVEL) -> None:
        """Forget earlier messages and start recording.

        Raises the log level to *level* so that messages below the suite's own
        level are not filtered out before they reach the recording, and remembers
        the level to put back when capturing stops. Pass ``NONE`` to leave the
        level untouched - useful when the test asserts what a *given* log level
        does and does not write.

        Capturing stops at the end of the test, so there is no need to stop it in
        a teardown.

        Args:
            level: Level to capture at, or ``NONE`` to keep the current one.

        Example:
            | Start Capturing Log Messages |
            | Start Capturing Log Messages | level=WARN |
        """
        self._stop()
        self._messages = []
        if str(level).upper() != NO_LEVEL_CHANGE:
            self._restore_level = self._set_log_level(level)
        self._capturing = True

    @keyword
    def stop_capturing_log_messages(self) -> List[Dict[str, str]]:
        """Stop recording, put the log level back, and return what was captured.

        Needed only when a test logs something afterwards that it does not want
        recorded; otherwise capturing ends with the test.

        Returns:
            The captured messages, as ``Get Captured Log Messages`` returns them.

        Example:
            | ${messages}= | Stop Capturing Log Messages |
        """
        messages = self.get_captured_log_messages()
        self._stop()
        return messages

    @keyword
    def get_captured_log_messages(self, level: Optional[str] = None,
                                  pattern: Optional[str] = None) -> List[Dict[str, str]]:
        """Return the captured messages, oldest first, optionally filtered.

        Each message is a dictionary with ``level``, ``message``, ``timestamp``
        and ``html`` - so a test can read ``${messages}[0][level]``.

        Both filters are matched against the message as Robot recorded it:
        ``level`` exactly and case-insensitively, ``pattern`` as a
        case-sensitive glob, so a partial match needs ``*`` around it.

        Args:
            level: Keep only messages logged at this level.
            pattern: Keep only messages whose text matches this glob.

        Returns:
            Copies of the matching messages, so the caller cannot disturb the
            recording.

        Example:
            | ${warnings}= | Get Captured Log Messages | level=WARN |
            | ${rotations}= | Get Captured Log Messages | pattern=*rotated* |
        """
        wanted_level = None if level is None else str(level).upper()
        return [dict(message) for message in self._messages
                if (wanted_level is None or message['level'].upper() == wanted_level)
                and (pattern is None or fnmatchcase(message['message'], pattern))]

    @keyword
    def captured_log_should_contain(self, pattern: str, level: Optional[str] = None,
                                    count: Optional[int] = None) -> None:
        """Fail unless a captured message matches *pattern*.

        The failure lists every message that was captured, because "the log line
        is missing" and "the log line is there at another level" need telling
        apart, and a bare assertion error cannot do that.

        Args:
            pattern: Case-sensitive glob the message text must match.
            level: Require the match to have been logged at this level.
            count: Require exactly this many matches rather than at least one.

        Example:
            | Captured Log Should Contain | *credentials rotated* |
            | Captured Log Should Contain | *retrying* | level=WARN | count=3 |
        """
        matches = self.get_captured_log_messages(level=level, pattern=pattern)
        if count is None:
            if matches:
                return
            problem = 'no captured message matches'
        else:
            if len(matches) == int(count):
                return
            problem = f'{len(matches)} captured messages match, expected {int(count)},'
        at_level = '' if level is None else f' at level {str(level).upper()}'
        raise AssertionError(f"{problem} '{pattern}'{at_level}. "
                             f'Captured: {self._describe_capture()}')

    # ------------------------------------------------------------------ internals

    def _stop(self) -> None:
        """Stop capturing and restore the log level if this library raised it."""
        self._capturing = False
        if self._restore_level is not None:
            self._set_log_level(self._restore_level)
            self._restore_level = None

    @staticmethod
    def _set_log_level(level: str) -> Optional[str]:
        """Set Robot's log level, returning the previous one.

        Returns ``None`` outside a Robot run - importing the library and calling
        its keywords from a unit test must not require a live Robot context.
        """
        try:
            return BuiltIn().set_log_level(level)
        except RobotNotRunningError:
            return None

    def _describe_capture(self) -> str:
        """Render the recording for a failure message."""
        if not self._messages:
            return 'nothing (was capturing started?)'
        return ', '.join(f"{message['level']} '{message['message']}'"
                         for message in self._messages)
