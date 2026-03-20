"""A dynamic Robot Framework library that cannot be resolved by _resolve_original_method."""


class DynamicLibrary:
    """Library using the dynamic API — keywords have no corresponding Python methods."""

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def get_keyword_names(self):
        return ['dynamic_greeting']

    def run_keyword(self, name, args, kwargs=None):
        if name == 'dynamic_greeting':
            return f"hello {args[0]}"
        raise ValueError(f"Unknown keyword: {name}")
