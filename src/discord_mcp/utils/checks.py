import inspect
import typing as t
from types import UnionType

from pydantic import validate_call

from discord_mcp.core.server.shared.context import DiscordMCPContext

__all__: tuple[str, ...] = (
    "issubclass_safe",
    "is_class_member_of_type",
    "find_kwarg_by_type",
    "context_safe_validate_call",
    "autocomplete_validate_argument_name",
    "autocomplete_validate_resource_template",
)


def issubclass_safe(cls: type, base: type) -> bool:
    """Check if cls is a subclass of base, even if cls is a type variable."""
    try:
        if origin := t.get_origin(cls):
            return issubclass_safe(origin, base)
        return issubclass(cls, base)
    except TypeError:
        return False


def is_class_member_of_type(cls: type, base: type) -> bool:
    """
    Check if cls is a member of base, even if cls is a type variable.

    Base can be a type, a UnionType, or an Annotated type. Generic types are not
    considered members (e.g. T is not a member of list[T]).
    """
    origin = t.get_origin(cls)
    # Handle both types of unions: UnionType (from types module, used with | syntax)
    # and typing.Union (used with Union[] syntax)
    if origin is UnionType or origin == t.Union:
        return any(is_class_member_of_type(arg, base) for arg in t.get_args(cls))
    elif origin is t.Annotated:
        # For Annotated[T, ...], check if T is a member of base
        args = t.get_args(cls)
        if args:
            return is_class_member_of_type(args[0], base)
        return False
    else:
        return issubclass_safe(cls, base)


def find_kwarg_by_type(fn: t.Callable[..., t.Any], kwarg_type: t.Type[t.Any]) -> str | None:
    """
    Find the name of the kwarg that is of type kwarg_type.

    Includes union types that contain the kwarg_type, as well as Annotated types.
    """
    if inspect.ismethod(fn) and hasattr(fn, "__func__"):
        fn = fn.__func__

    # Try to get resolved type hints
    try:
        # Use include_extras=True to preserve Annotated metadata
        type_hints = t.get_type_hints(fn, include_extras=True)
    except Exception:
        # If resolution fails, use raw annotations if they exist
        type_hints = getattr(fn, "__annotations__", {})

    sig = inspect.signature(fn)
    for name, param in sig.parameters.items():
        # Use resolved hint if available, otherwise raw annotation
        annotation = type_hints.get(name, param.annotation)
        if is_class_member_of_type(annotation, kwarg_type):
            return name
    return None


def context_safe_validate_call(fn: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:
    """Creates a validator with the same signature that returns the original function."""

    sig = inspect.signature(fn)
    if annotations := getattr(fn, "__annotations__", {}):
        try:
            annotations = t.get_type_hints(fn, globalns=getattr(fn, "__globals__", {}))
        except (NameError, AttributeError):
            # Fall back to original annotations if resolution fails
            pass

    def validator(*args: t.Any, **kwargs: t.Any) -> t.Callable[..., t.Any]:
        return fn

    # Copy the signature and annotations to the validator
    validator.__signature__ = sig  # type: ignore
    validator.__annotations__ = annotations
    validator.__doc__ = fn.__doc__
    validator.__name__ = fn.__name__

    return validate_call(validator)


def autocomplete_validate_argument_name(
    fn: t.Callable[..., t.Any],
    argument_name: str,
) -> None:
    sig = inspect.signature(fn)
    if argument_name not in sig.parameters:
        raise RuntimeError(
            f"'autocomplete' is completing {argument_name!r} but it's not an argument of {fn.__name__!r}!"
        )


def autocomplete_validate_resource_template(
    fn: t.Callable[..., t.Any],
    uri: str,
) -> None:
    has_uri_params = "{" in uri and "}" in uri
    has_func_params = any(
        p for p in inspect.signature(fn).parameters.values() if p.name != find_kwarg_by_type(fn, DiscordMCPContext)
    )

    if not (has_uri_params or has_func_params):
        raise RuntimeError(
            "'autocomplete' cannot be used on normal resources. It can only be used on resource templates and prompts."
        )
