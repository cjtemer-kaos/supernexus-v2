"""SuperNEXUS v2.0 - Core modules"""

# Global Windows UTF-8 protection patch (inspired by openswarm)
import sys
if sys.platform.startswith("win"):
    import builtins
    original_open = builtins.open
    def patched_open(*args, **kwargs):
        if "encoding" not in kwargs and (len(args) < 4 or args[3] is None):
            mode = kwargs.get("mode", "r") if len(args) < 2 else args[1]
            if "b" not in mode:
                kwargs["encoding"] = "utf-8"
        return original_open(*args, **kwargs)
    builtins.open = patched_open
