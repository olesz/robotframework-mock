"""Shared internals for the mock libraries.

Private package - not part of the public API, and not meant to be imported by
tests. ``MockLibrary`` and ``MockResource`` both keep their mocked keywords in a
``self._mocks`` mapping of :class:`unittest.mock.Mock` objects, which already
record every call. The keywords that expose those recorded calls are therefore
implemented once here and mixed into both libraries, so the two cannot drift
apart.
"""
# pylint: disable=invalid-name
from typing import Any, Dict, List
from unittest.mock import call

from robot.api.deco import keyword


class CallInspectionMixin:
    """Keywords for inspecting how a mocked keyword was called.

    The host library must provide:

    - ``self._mocks``: mapping of mock key -> :class:`unittest.mock.Mock`
    - ``self._mock_key(keyword_name)``: the ``self._mocks`` key for a keyword
      name, in case the library does not key by the name as written
    """

    _mocks: Dict[str, Any]

    def _mock_key(self, keyword_name: str) -> str:
        """Return the ``self._mocks`` key for *keyword_name*.

        Args:
            keyword_name: Keyword name as written in the test.

        Returns:
            The key under which the mock is stored. Libraries that normalise
            keyword names override this.
        """
        return keyword_name

    def _get_mock(self, keyword_name: str):
        """Return the mock for *keyword_name*.

        Args:
            keyword_name: Name of the mocked keyword.

        Returns:
            The :class:`unittest.mock.Mock` backing that keyword.

        Raises:
            AssertionError: If the keyword was not mocked.
        """
        key = self._mock_key(keyword_name)
        if key not in self._mocks:
            raise AssertionError(f"Keyword '{keyword_name}' was not mocked")
        return self._mocks[key]

    def _get_call(self, keyword_name: str, index):
        """Return a single recorded call.

        Args:
            keyword_name: Name of the mocked keyword.
            index: Zero-based call index. Negative values count from the end,
                so ``-1`` is the most recent call.

        Returns:
            The :class:`unittest.mock.call` recorded at that index.

        Raises:
            AssertionError: If the keyword was not mocked, or fewer calls were
                recorded than *index* requires.
        """
        calls = self._get_mock(keyword_name).call_args_list
        index = int(index)
        if not -len(calls) <= index < len(calls):
            raise AssertionError(
                f"No call recorded at index {index} for keyword "
                f"'{keyword_name}', it was called {len(calls)} time(s)"
            )
        return calls[index]

    @keyword
    def get_keyword_call_count(self, keyword_name: str) -> int:
        """Return how many times a mocked keyword was called.

        Args:
            keyword_name: Name of the mocked keyword.

        Returns:
            The number of recorded calls.

        Raises:
            AssertionError: If the keyword was not mocked.

        Example:
            | ${count}= | MockDB.Get Keyword Call Count | Execute Sql |
        """
        return self._get_mock(keyword_name).call_count

    @keyword
    def get_keyword_call_args(self, keyword_name: str, index=0) -> List[Any]:
        """Return the positional arguments of one call to a mocked keyword.

        Args:
            keyword_name: Name of the mocked keyword.
            index: Zero-based call index, negative counts from the end.

        Returns:
            The positional arguments of that call.

        Raises:
            AssertionError: If the keyword was not mocked or the call does not
                exist.

        Example:
            | ${args}= | MockDB.Get Keyword Call Args | Execute Sql | index=0 |
            | Should Be Equal | ${args}[0] | SELECT 1 |
        """
        return list(self._get_call(keyword_name, index).args)

    @keyword
    def get_keyword_call_kwargs(self, keyword_name: str, index=0) -> Dict[str, Any]:
        """Return the named arguments of one call to a mocked keyword.

        Args:
            keyword_name: Name of the mocked keyword.
            index: Zero-based call index, negative counts from the end.

        Returns:
            The named arguments of that call.

        Raises:
            AssertionError: If the keyword was not mocked or the call does not
                exist.

        Example:
            | ${kwargs}= | MockDB.Get Keyword Call Kwargs | Execute Sql |
            | Should Be Equal | ${kwargs}[timeout] | 30 |
        """
        return dict(self._get_call(keyword_name, index).kwargs)

    @keyword
    def verify_keyword_called_with(self, keyword_name: str, *args, **kwargs):
        """Verify a mocked keyword was called with the given arguments.

        Passes when **at least one** recorded call matches exactly, which keeps
        the check usable when the order of calls is not significant. Use
        :meth:`get_keyword_call_args` to assert on a specific call instead.

        Arguments are compared with Python equality, so types matter. Robot
        passes test data as strings but converts arguments of typed library
        keywords first, so such a value must be given as a typed Robot variable
        (``base=${16}``, not ``base=16``) to match what was recorded.

        Args:
            keyword_name: Name of the mocked keyword.
            *args: Expected positional arguments.
            **kwargs: Expected named arguments.

        Raises:
            AssertionError: If the keyword was not mocked, or no recorded call
                matches.

        Example:
            | MockDB.Verify Keyword Called With | Execute Sql | SELECT 1 |
        """
        mock = self._get_mock(keyword_name)
        expected = call(*args, **kwargs)
        if expected not in mock.call_args_list:
            actual = (
                '\n'.join(f'  {index}: {item}'
                          for index, item in enumerate(mock.call_args_list))
                or '  (never called)'
            )
            raise AssertionError(
                f"Keyword '{keyword_name}' was not called with {expected}.\n"
                f"Recorded calls:\n{actual}"
            )
