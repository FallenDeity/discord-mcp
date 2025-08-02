import os
import pkgutil
import typing as t

__all__: tuple[str, ...] = ("search_directory",)


def search_directory(path: str) -> t.Iterator[str]:
    """Walk through a directory and yield all modules.

    Parameters
    ----------
    path: :class:`str`
        The path to search for modules

    Yields
    ------
    :class:`str`
        The name of the found module. (usable in load_extension)
    """
    relpath = os.path.relpath(path)  # relative and normalized
    if ".." in relpath:
        raise ValueError("Modules outside the cwd require a package to be specified")

    abspath = os.path.abspath(path)
    if not os.path.exists(relpath):
        raise ValueError(f"Provided path '{abspath}' does not exist")
    if not os.path.isdir(relpath):
        raise ValueError(f"Provided path '{abspath}' is not a directory")

    prefix = relpath.replace(os.sep, ".")
    if prefix in ("", "."):
        prefix = ""
    else:
        prefix += "."

    for _, name, ispkg in pkgutil.iter_modules([path]):
        if ispkg:
            yield from search_directory(os.path.join(path, name))
        else:
            yield prefix + name
