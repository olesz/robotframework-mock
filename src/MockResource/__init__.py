"""Mock resource for Robot Framework keyword mocking in unit tests."""
# pylint: disable=invalid-name
import weakref
from typing import Any, Callable
from unittest.mock import Mock

from robot.api.deco import keyword
from robot.libraries.BuiltIn import BuiltIn
from robot.running import Return
from robot.running.namespace import Namespace
from robot.utils import split_from_equals

from _mock_core import (
    CallInspectionMixin,
    normalize_keyword_name,
    register_mocked_keyword,
    unregister_mocked_keyword,
)

# Robot resolves the values of a RETURN statement as variable expressions, so a
# mocked return value cannot be embedded in one directly - anything that is not
# a string raises a TypeError. The value is therefore published under this name
# and the injected RETURN refers to it, which lets a mock return any Python
# object (a query result set, a parsed JSON body, a list of pods...).
RETURN_VARIABLE = '${__mock_resource_return__}'

# Namespace.get_runner is patched once per process rather than once per
# MockResource instance. Patching per instance chained a new wrapper around the
# previous one for every library import, and nothing ever restored them, so
# every keyword lookup in the run paid for each import. The single wrapper
# consults the live instances below and is inert when none of them has mocks.
_INSTANCES = []
_ORIGINAL_GET_RUNNER = None


def _live_instances():
    """Return the MockResource instances that are still alive.

    Instances are held weakly so a library instance going out of scope does not
    keep its mocks alive, and dead references are pruned on access.

    Returns:
        The live instances, in the order they were created.
    """
    live = []
    for reference in list(_INSTANCES):
        instance = reference()
        if instance is None:
            _INSTANCES.remove(reference)
        else:
            live.append(instance)
    return live


def _install_shared_patch():
    """Patch ``Namespace.get_runner`` once, routing to all live instances."""
    global _ORIGINAL_GET_RUNNER  # pylint: disable=global-statement
    if _ORIGINAL_GET_RUNNER is not None:
        return
    _ORIGINAL_GET_RUNNER = Namespace.get_runner
    original_get_runner = _ORIGINAL_GET_RUNNER

    def patched_get_runner(self, keyword_name, recommend_on_failure):
        keyword_runner = original_get_runner(self, keyword_name, recommend_on_failure)
        resource_file = getattr(keyword_runner.keyword, "source", None)

        for instance in _live_instances():
            if instance.source not in str(resource_file):
                continue
            mock = instance.mocks.get(normalize_keyword_name(keyword_name))
            if not mock:
                continue
            original_run = keyword_runner.run

            def patched_run(data, result, context, run,
                            _mock=mock, _original_run=original_run):
                args, kwargs = _resolve_arguments(
                    keyword_runner.keyword, data, context
                )
                mock_result = _mock(*args, **kwargs)
                # Test scope, so the value is visible to the keyword's own
                # body even when the mocked keyword is called from inside
                # another keyword rather than directly from the test.
                context.variables.set_test(RETURN_VARIABLE, mock_result)
                keyword_runner.keyword.body._items = [Return(values=[RETURN_VARIABLE])]  # pylint: disable=protected-access
                return _original_run(data, result, context, run)

            keyword_runner.run = patched_run
            break

        return keyword_runner

    Namespace.get_runner = patched_get_runner


def _resolve_arguments(keyword_obj, data, context):
    """Split a keyword call's raw arguments into resolved args and kwargs.

    Robot hands the listener the argument list exactly as written at the call
    site, so variables are still unresolved (``${query} commit;``) and named
    arguments are plain ``name=value`` strings. Both are resolved here so that
    mocks record what the keyword was *really* called with, matching what
    ``MockLibrary`` records for library keywords.

    A ``name=value`` item only becomes a named argument when ``name`` is an
    argument the keyword actually declares; otherwise it stays positional, so a
    value that merely contains ``=`` is not misread.

    Args:
        keyword_obj: The keyword being called, used for its argument spec.
        data: Robot keyword call data holding the raw arguments.
        context: Robot execution context, used to resolve variables.

    Returns:
        A ``(args, kwargs)`` tuple of resolved arguments.
    """
    spec = getattr(keyword_obj, 'args', None)
    accepted = set()
    if spec is not None:
        accepted.update(spec.positional or ())
        accepted.update(spec.named_only or ())

    args = []
    kwargs = {}
    for argument in context.variables.replace_list(data.args):
        name, value = (
            split_from_equals(argument) if isinstance(argument, str)
            else (None, None)
        )
        if value is not None and name in accepted:
            kwargs[name] = value
        else:
            args.append(argument)
    return args, kwargs


class MockResource(CallInspectionMixin):
    """Mock keywords from Robot Framework resource files for unit testing.
    
    Example:
        | Library | MockResource | my_resource.robot | WITH NAME | MockRes |
        | MockRes.Mock Keyword | My Keyword | return_value=test_data |
        | My Keyword |
        | MockRes.Reset Mocks |
    """

    def __init__(self, source):
        self._source = source
        self._original_items = {}
        self._original_setups = {}
        self._original_teardowns = {}
        self._mocked_sources = {}
        self._mocks = {}
        _INSTANCES.append(weakref.ref(self))
        _install_shared_patch()

    @property
    def source(self):
        """Return the resource file this instance mocks keywords from."""
        return self._source

    @property
    def mocks(self):
        """Return the active mocks, keyed by normalized keyword name."""
        return self._mocks

    def _mock_key(self, keyword_name: str) -> str:
        """Return the ``self._mocks`` key for *keyword_name*.

        Mocks are keyed the way Robot Framework matches keyword names, so
        inspecting a call works whatever case or spacing the test used.

        Args:
            keyword_name: Keyword name as written in the test.

        Returns:
            The normalized name used as the mock key.
        """
        return normalize_keyword_name(keyword_name)

    @keyword
    def mock_keyword(
        self, keyword_name: str,
        return_value: Any = None, side_effect: Callable = None,
        skip_setup: bool = False, skip_teardown: bool = False
    ):
        """Mock a keyword from the resource file.

        Only the keyword's body is replaced. Its ``[Setup]`` and ``[Teardown]``
        still run by default, which keeps them observable - a test can assert
        that a teardown released a lock, for example. Suppress them when the
        mocked keyword's own setup or teardown is an implementation detail the
        test should not depend on, typically because it cleans up state that the
        replaced body would have created and therefore fails.

        Args:
            keyword_name: Name of the keyword to mock
            return_value: Value to return when the keyword is called. May be any
                Python object.
            side_effect: Callable to execute instead of returning a value.
                Receives the call's resolved arguments, the same way a
                ``MockLibrary`` side effect does.
            skip_setup: Do not run the keyword's ``[Setup]`` while mocked.
            skip_teardown: Do not run the keyword's ``[Teardown]`` while mocked.

        Returns:
            The :class:`unittest.mock.Mock` backing the keyword.

        Raises:
            AttributeError: If the keyword is not found in the resource file.

        Example:
            | MockRes.Mock Keyword | My Keyword | return_value=test_data |
            | MockRes.Mock Keyword | Init Client | skip_teardown=${True} |
        """
        keyword_runner = BuiltIn()._namespace.get_runner(keyword_name, True)  # pylint: disable=protected-access
        resource_file = getattr(keyword_runner.keyword, "source", None)

        if self._source not in str(resource_file):
            raise AttributeError(
                f"Keyword '{keyword_name}' not found in {self._source}"
            )

        self._original_items[keyword_name] = keyword_runner.keyword.body._items  # pylint: disable=protected-access
        self._mocked_sources[keyword_name] = resource_file
        if skip_setup:
            self._original_setups[keyword_name] = keyword_runner.keyword.setup
            keyword_runner.keyword.setup = None
        if skip_teardown:
            self._original_teardowns[keyword_name] = keyword_runner.keyword.teardown
            keyword_runner.keyword.teardown = None
        mock = Mock(return_value=return_value, side_effect=side_effect)
        self._mocks[normalize_keyword_name(keyword_name)] = mock
        # Tell MockCoverage this keyword's body no longer runs, so it is not
        # credited with coverage it did not earn.
        register_mocked_keyword(resource_file, keyword_name)
        return mock

    @keyword
    def reset_mocks(self):
        """Reset all mocks to their original implementations.
        
        Restores all mocked keywords to their original behavior, including any
        ``[Setup]`` or ``[Teardown]`` that was suppressed while mocked.

        Example:
            | MockRes.Reset Mocks |
        """
        self._mocks.clear()
        for keyword_name, source in self._mocked_sources.items():
            unregister_mocked_keyword(source, keyword_name)
        for keyword_name, items in self._original_items.items():
            keyword_runner = BuiltIn()._namespace.get_runner(keyword_name, True)  # pylint: disable=protected-access
            keyword_runner.keyword.body._items = items  # pylint: disable=protected-access
        for keyword_name, setup in self._original_setups.items():
            keyword_runner = BuiltIn()._namespace.get_runner(keyword_name, True)  # pylint: disable=protected-access
            keyword_runner.keyword.setup = setup
        for keyword_name, teardown in self._original_teardowns.items():
            keyword_runner = BuiltIn()._namespace.get_runner(keyword_name, True)  # pylint: disable=protected-access
            keyword_runner.keyword.teardown = teardown
        self._original_items.clear()
        self._original_setups.clear()
        self._original_teardowns.clear()
        self._mocked_sources.clear()

    @keyword
    def verify_keyword_called(self, keyword_name: str, times: int = None):
        """Verify that a mocked keyword was called.
        
        Args:
            keyword_name: Name of the keyword to verify
            times: Expected number of calls (optional)
        
        Raises:
            AssertionError: If keyword was not mocked or call count doesn't match

        Example:
            | MockDB.Verify Keyword Called | Execute Sql | times=1 |
        """
        mock = self._get_mock(keyword_name)
        if times is not None and mock.call_count != times:
            raise AssertionError(f"Expected {times} calls, got {mock.call_count}")
