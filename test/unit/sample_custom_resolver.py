"""Sample custom resolver for unit tests."""


class SampleResolver:  # pylint: disable=too-few-public-methods
    """Resolver that delegates to getattr for keyword resolution."""

    def resolve_original_method(self, lib, method_name, _keyword_name, _side_effect):
        """Resolve a keyword by direct attribute lookup."""
        try:
            return getattr(lib, method_name), method_name
        except AttributeError:
            return None, method_name
