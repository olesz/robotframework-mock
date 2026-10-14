"""Call order recorded across every mock instance.

``MockLibrary`` and ``MockResource`` each report the order of the calls *they*
mocked, which cannot show how calls to different instances interleaved: a mock
records its invocation order on its parent, and ``unittest.mock`` gives a mock
exactly one parent, so the per-instance records cannot be merged after the fact.
Every mocked call is therefore also noted on one shared timeline, which this
library reads.

It is a library of its own rather than two more keywords on the mock instances
because the timeline belongs to none of them. Putting it on the instances would
make every instance expose the same keyword, so a suite with two mocks - the only
situation where a cross-instance order is interesting - could not call it without
picking one instance to ask, which reads as if the answer were that instance's.

Example:
    | Library | MockResource | db.resource | AS | MockDb |
    | Library | MockResource | alarm.resource | AS | MockAlarm |
    | Library | MockCallOrder |
    |  |  |
    | Reset Global Call Order |
    | MockAlarm.Mock Keyword | Wait For Alarm | return_value=${None} |
    | MockDb.Mock Keyword | Run Query | return_value=${rows} |
    | Refresh Data |
    | ${order}= | Get Global Call Order |
    | Should Be Equal | ${order} | ${{ ['Wait For Alarm', 'Run Query'] }} |
"""
# pylint: disable=invalid-name
from typing import List

from robot.api.deco import keyword

from _mock_core import GLOBAL_CALL_TIMELINE


class MockCallOrder:
    """Read and reset the call order recorded across all mock instances."""

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    @keyword
    def get_global_call_order(self, qualified: bool = False) -> List[str]:
        """Return mocked keywords from *every* mock instance, in call order.

        ``Get Keyword Call Order`` is limited to one library instance, so it
        cannot show how calls to different instances interleaved. Where that
        interleaving is the contract under test - "raise the alarm, restart, then
        wait for it to clear", with the alarm and the restart mocked through
        different instances - this is the keyword that can assert it.

        A keyword called more than once appears once per call, and a call that
        raised is still a call, so retry sequences are visible too. Keywords
        mocked but never called do not appear.

        The order is recorded as the calls happen and is **not** cleared by any
        instance's ``Reset Mocks``: resetting one instance must not discard
        another instance's history. Clear it with ``Reset Global Call Order``,
        normally from the test setup.

        Args:
            qualified: When true, each name is prefixed with the library or
                resource it was mocked on, e.g.
                ``kubelibrary.resource.Get First POD``. Use it when two mocked
                targets define the same keyword name.

        Returns:
            Keyword names, as written when mocking, in invocation order.

        Example:
            | Reset Global Call Order |
            | MockRes.Mock Keyword | Open Tunnel | return_value=${port} |
            | MockLib.Mock Keyword | Connect To Database | return_value=${None} |
            | Fetch Data |
            | ${order}= | Get Global Call Order |
            | Should Be Equal | ${order} | ${{ ['Open Tunnel', 'Connect To Database'] }} |
        """
        if qualified:
            return [f'{target}.{name}' for target, name in GLOBAL_CALL_TIMELINE]
        return [name for _, name in GLOBAL_CALL_TIMELINE]

    @keyword
    def reset_global_call_order(self) -> None:
        """Forget the call order recorded across all mock instances.

        Call it before the mocks whose order a test asserts are installed -
        usually from the suite's test setup, so one test cannot see another's
        calls.

        Example:
            | Reset Global Call Order |
        """
        GLOBAL_CALL_TIMELINE.clear()
