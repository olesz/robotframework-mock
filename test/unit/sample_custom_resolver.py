"""Sample custom resolver for unit tests."""


class SampleResolver:
    """Resolver that delegates to getattr but uppercases the method name suffix."""

    def resolve_original_method(self, lib, method_name, keyword_name, side_effect):
        try:
            return getattr(lib, method_name), method_name
        except AttributeError:
            return None, method_name
