# pylint: disable=invalid-name
"""Static test library used by the call-inspection keyword tests.

The keywords below declare no argument types and default to strings, so every
supported Robot Framework version passes the test data through unchanged and the
recorded arguments are the strings written in the test.

Built-in keywords are unsuitable for this: the type hints on them differ between
Robot Framework versions, so the recorded argument types differ too. ``Convert
To Binary``, for example, records ``base=16`` as a string up to Robot Framework
7.3 and as an integer from 7.4 onwards.
"""
from robot.api.deco import keyword


class StaticLibrary:
    """Library whose arguments are recorded exactly as written in the test."""
    # pylint: disable=too-few-public-methods

    def execute_query(self, query, timeout='default'):
        """Return the arguments joined, so unmocked calls stay observable.

        Args:
            query: Any string.
            timeout: Any string.

        Returns:
            The two arguments separated by a pipe.
        """
        return f'{query}|{timeout}'

    @keyword('Is The Target Reachable')
    def check_target_reachability(self, target):
        """Return the target, under a keyword name unrelated to the method name.

        The ``@keyword`` decorator deliberately gives this a name that does not
        follow from ``check_target_reachability``, so mocking it only works if
        the decorator's name is honoured.

        Args:
            target: Any string.

        Returns:
            The target unchanged.
        """
        return target
