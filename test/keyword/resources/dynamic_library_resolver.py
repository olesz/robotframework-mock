"""Custom resolver for DynamicLibrary keywords."""
from functools import wraps


class DynamicLibraryResolver:

    def resolve_original_method(self, lib, method_name, keyword_name, side_effect):
        if not hasattr(lib, 'get_keyword_names'):
            return None, method_name
        kw_names = lib.get_keyword_names()
        if method_name not in kw_names:
            return None, method_name

        original_run_keyword = lib.run_keyword

        @wraps(original_run_keyword)
        def patched_run_keyword(name, args, kwargs=None):
            if name == method_name:
                mock = getattr(lib, method_name, None)
                if callable(mock):
                    return mock(name, args, kwargs)
            return original_run_keyword(name, args, kwargs)

        lib.run_keyword = patched_run_keyword
        return original_run_keyword, method_name
