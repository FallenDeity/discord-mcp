import functools
import inspect
import typing as t

import docstring_parser
import pydantic
from mcp.server.fastmcp import Context

from discord_mcp.utils.enums import ResourceReturnType

__all__: tuple[str, ...] = (
    "convert_name_to_title",
    "transform_function_signature",
    "extract_mime_type_from_fn_return",
    "add_description_to_annotation",
    "prune_param",
    "get_cached_typeadapter",
)


T = t.TypeVar("T")


def convert_name_to_title(name: str) -> str:
    """Convert a tool name to a human-readable title."""
    return name.replace("_", " ").title()


def add_description_to_annotation(ann: t.Any, default: t.Any, description: str) -> t.Tuple[t.Any, t.Any]:
    # Case 1: Annotated[ann, Field(...)]
    if t.get_origin(ann) is t.Annotated:
        base, *extras = t.get_args(ann)
        new_extras = []
        field_found = False

        for e in extras:
            if isinstance(e, pydantic.fields.FieldInfo):
                new_extras.append(
                    pydantic.fields.FieldInfo.merge_field_infos(e, pydantic.Field(description=description))
                )
                field_found = True
            else:
                new_extras.append(e)

        if not field_found:
            new_extras.append(pydantic.Field(description=description))

        return t.Annotated[base, *new_extras], default

    # Case 2: Default is Field(...)
    if isinstance(default, pydantic.fields.FieldInfo):
        return ann, pydantic.fields.FieldInfo.merge_field_infos(default, pydantic.Field(description=description))

    # Case 3: No Field, wrap in Annotated
    return t.Annotated[ann, pydantic.Field(description=description)], default


def transform_function_signature(fn: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:
    """Transform a function's signature to include type hints and docstring descriptions from the docstring."""
    sig = inspect.signature(fn)
    doc = inspect.getdoc(fn) or ""
    parsed_doc = docstring_parser.parse(doc)

    param_desc_map = {p.arg_name: (p.description, p.type_name) for p in parsed_doc.params if p.description}

    # if any param is untyped or *args/**kwargs raise an error
    for p in sig.parameters.values():
        if p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            raise TypeError("*args/**kwargs are not allowed in MCP tools")
        _, type_name = param_desc_map.get(p.name, (None, None))
        if p.annotation is inspect._empty and not type_name:
            raise TypeError(f"Parameter '{p.name}' must be typed")

    updated_params: list[inspect.Parameter] = []
    for name, param in sig.parameters.items():
        ann, default = param.annotation, param.default
        if issubclass(param.annotation, Context):
            continue
        if name in param_desc_map:
            description, type_name = param_desc_map[name]
            ann = type_name if ann is inspect._empty and type_name else ann
            ann, default = add_description_to_annotation(ann, default, description)
        updated_params.append(param.replace(annotation=ann, default=default))

    updated_sig = sig.replace(parameters=updated_params) if updated_params else sig

    fn.__signature__ = updated_sig  # type: ignore
    fn.__doc__ = parsed_doc.short_description or ""
    fn.__name__ = fn.__name__
    return fn


def extract_mime_type_from_fn_return(fn: t.Callable[..., t.Any]) -> str:
    sig = inspect.signature(fn)
    return_annotation = t.get_type_hints(fn, include_extras=True).get("return", inspect._empty)
    r_type = (
        return_annotation
        if not t.get_args(return_annotation) and return_annotation in ResourceReturnType._value2member_map_.keys()
        else (t.get_origin(return_annotation) if t.get_args(return_annotation) else return_annotation)
    )

    match r_type:
        case ResourceReturnType.STR.value:
            return "text/plain"
        case ResourceReturnType.BYTES.value:
            return "application/octet-stream"
        case ResourceReturnType.LIST.value | ResourceReturnType.DICT.value | ResourceReturnType.NONE.value:
            return "application/json"
        case inspect._empty:
            raise TypeError("Resources must have a return type annotation!")
        case _:
            if issubclass(r_type, ResourceReturnType.PYDANTIC_BASE_MODEL.value):
                return "application/json"

            name = getattr(sig.return_annotation, "__name__", sig.return_annotation.__class__.__name__)
            raise RuntimeError(
                f"Resources return type must be `str`, `bytes`, `list`, `dict`, `None` or a pydantic `BaseModel` subclasss, got {name!r}"
            )


def prune_param(schema: dict[str, t.Any], param: str) -> dict[str, t.Any]:
    """Return a new schema with *param* removed from `properties`, `required`,
    and (if no longer referenced) `$defs`.
    """

    # Drop from properties/required
    props = schema.get("properties", {})
    removed = props.pop(param, None)
    if removed is None:  # nothing to do
        return schema

    # Keep empty properties object rather than removing it entirely
    schema["properties"] = props
    if param in schema.get("required", []):
        schema["required"].remove(param)
        if not schema["required"]:
            schema.pop("required")

    return schema


@functools.lru_cache(maxsize=5000)
def get_cached_typeadapter(cls: T) -> pydantic.TypeAdapter[T]:
    """
    TypeAdapters are heavy objects, and in an application context we'd typically
    create them once in a global scope and reuse them as often as possible.
    However, this isn't feasible for user-generated functions. Instead, we use a
    cache to minimize the cost of creating them as much as possible.
    """
    # For functions, process annotations to handle forward references and convert
    # Annotated[Type, "string"] to Annotated[Type, Field(description="string")]

    # print signature of the function
    if inspect.isfunction(cls) or inspect.ismethod(cls):
        if hasattr(cls, "__annotations__") and cls.__annotations__:
            try:
                # Resolve forward references first
                resolved_hints = t.get_type_hints(cls, include_extras=True)
            except Exception:
                # If forward reference resolution fails, use original annotations
                resolved_hints = cls.__annotations__

            # Process annotations to convert string descriptions to Fields
            processed_hints = {}

            for name, annotation in resolved_hints.items():
                # Check if this is Annotated[Type, "string"] and convert to Annotated[Type, Field(description="string")]
                if (
                    t.get_origin(annotation) is t.Annotated
                    and len(t.get_args(annotation)) == 2
                    and isinstance(t.get_args(annotation)[1], str)
                ):
                    base_type, description = t.get_args(annotation)
                    processed_hints[name] = t.Annotated[base_type, pydantic.Field(description=description)]
                else:
                    processed_hints[name] = annotation

            # Create new function if annotations changed
            if processed_hints != cls.__annotations__:
                import types

                # Handle both functions and methods
                if inspect.ismethod(cls):
                    actual_func = cls.__func__
                    code = actual_func.__code__
                    globals_dict = actual_func.__globals__
                    name = actual_func.__name__
                    defaults = actual_func.__defaults__
                    closure = actual_func.__closure__
                else:
                    code = cls.__code__
                    globals_dict = cls.__globals__
                    name = cls.__name__
                    defaults = cls.__defaults__
                    closure = cls.__closure__

                new_func = types.FunctionType(
                    code,
                    globals_dict,
                    name,
                    defaults,
                    closure,
                )
                new_func.__dict__.update(cls.__dict__)
                new_func.__module__ = cls.__module__
                new_func.__qualname__ = getattr(cls, "__qualname__", cls.__name__)
                new_func.__annotations__ = processed_hints

                return pydantic.TypeAdapter(new_func)

    return pydantic.TypeAdapter(cls)
