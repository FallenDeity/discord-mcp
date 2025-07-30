import typing as t


def inject_function(fn: t.Callable[..., t.Any], attrs: dict[str, t.Any]) -> None:
    for k, v in attrs.items():
        fn.__setattr__(f"__discord_mcp_{k}__", v)
