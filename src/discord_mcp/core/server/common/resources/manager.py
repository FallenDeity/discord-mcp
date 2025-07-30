from __future__ import annotations

import inspect
import logging
import re
import typing as t

import pydantic_core
from mcp.server.fastmcp.resources import FunctionResource, ResourceManager, ResourceTemplate
from mcp.server.fastmcp.resources.base import Resource

# TODO: Deal with validate call issues here
from pydantic import AnyUrl  # , validate_call

from discord_mcp.core.server.common.context import DiscordMCPContext, get_context
from discord_mcp.utils.checks import find_kwarg_by_type
from discord_mcp.utils.converters import get_cached_typeadapter, prune_param

__all__: tuple[str, ...] = (
    "DiscordMCPResourceManager",
    "DiscordMCPFunctionResource",
)


logger = logging.getLogger(__name__)


class DiscordMCPFunctionResource(FunctionResource):
    async def read(self) -> str | bytes:
        """Read the resource by calling the wrapped function."""
        try:
            # Call the function first to see if it returns a coroutine
            context_kwarg = find_kwarg_by_type(self.fn, DiscordMCPContext)
            result = self.fn() if not context_kwarg else self.fn(**{context_kwarg: get_context()})
            # If it's a coroutine, await it
            if inspect.iscoroutine(result):
                result = await result

            if isinstance(result, Resource):
                return await result.read()
            elif isinstance(result, (str, bytes)):
                return result
            else:
                return pydantic_core.to_json(result, fallback=str, indent=2).decode()
        except Exception as e:
            raise ValueError(f"Error reading resource {self.uri}: {e}")

    @classmethod
    def from_function(
        cls,
        fn: t.Callable[..., t.Any],
        uri: str,
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        mime_type: str | None = None,
    ) -> FunctionResource:
        fn_res = super().from_function(fn, uri, name, title, description, mime_type)
        fn_res.fn = fn
        return fn_res


class DiscordMCPResourceTemplate(ResourceTemplate):
    @classmethod
    def from_function(
        cls,
        fn: t.Callable[..., t.Any],
        uri_template: str,
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        mime_type: str | None = None,
    ) -> ResourceTemplate:
        func_name = name or getattr(fn, "__name__", None) or fn.__class__.__name__
        if func_name == "<lambda>":
            raise ValueError("You must provide a name for lambda functions")

        # Reject functions with *args
        # (**kwargs is allowed because the URI will define the parameter names)
        sig = inspect.signature(fn)
        for param in sig.parameters.values():
            if param.kind == inspect.Parameter.VAR_POSITIONAL:
                raise ValueError("Functions with *args are not supported as resource templates")

        context_kwarg = find_kwarg_by_type(fn, kwarg_type=DiscordMCPContext)

        # Validate that URI params match function params
        uri_params = set(re.findall(r"{(\w+)(?:\*)?}", uri_template))
        if not uri_params:
            raise ValueError("URI template must contain at least one parameter")

        func_params = set(sig.parameters.keys())
        if context_kwarg:
            func_params.discard(context_kwarg)

        # get the parameters that are required
        required_params = {
            p
            for p in func_params
            if sig.parameters[p].default is inspect.Parameter.empty
            and sig.parameters[p].kind != inspect.Parameter.VAR_KEYWORD
            and p != context_kwarg
        }

        # Check if required parameters are a subset of the URI parameters
        if not required_params.issubset(uri_params):
            raise ValueError(
                f"Required function arguments {required_params} must be a subset of the URI parameters {uri_params}"
            )

        # Check if the URI parameters are a subset of the function parameters (skip if **kwargs present)
        if not any(param.kind == inspect.Parameter.VAR_KEYWORD for param in sig.parameters.values()):
            if not uri_params.issubset(func_params):
                raise ValueError(
                    f"URI parameters {uri_params} must be a subset of the function arguments: {func_params}"
                )

        description = description or inspect.getdoc(fn)

        parameters = get_cached_typeadapter(fn).json_schema()
        parameters = prune_param(parameters, param=context_kwarg) if context_kwarg else parameters

        # ensure the arguments are properly cast
        # fn = validate_call(fn) fails if not commented

        return cls(
            uri_template=uri_template,
            name=func_name,
            title=title,
            description=description,
            mime_type=mime_type or "text/plain",
            fn=fn,
            parameters=parameters,
        )

    async def create_resource(self, uri: str, params: dict[str, t.Any]) -> Resource:
        try:
            # Call function and check if result is a coroutine
            result = self.fn(**params)
            if inspect.iscoroutine(result):
                result = await result

            return DiscordMCPFunctionResource(
                uri=uri,  # type: ignore
                name=self.name,
                title=self.title,
                description=self.description,
                mime_type=self.mime_type,
                fn=lambda: result,  # Capture result in closure
            )
        except Exception as e:
            raise ValueError(f"Error creating resource from template: {e}")


class DiscordMCPResourceManager(ResourceManager):
    async def get_resource(self, uri: AnyUrl | str) -> Resource | None:
        """Get resource by URI, checking concrete resources first, then templates."""
        uri_str = str(uri)
        logger.debug("Getting resource", extra={"uri": uri_str})

        # First check concrete resources
        if resource := self._resources.get(uri_str):
            return resource

        # Then check templates
        for template in self._templates.values():
            if params := template.matches(uri_str):
                try:
                    context_kwarg = find_kwarg_by_type(template.fn, DiscordMCPContext)
                    params |= {context_kwarg: get_context()} if context_kwarg else {}
                    return await template.create_resource(uri_str, params)
                except Exception as e:
                    raise ValueError(f"Error creating resource from template: {e}")

        raise ValueError(f"Unknown resource: {uri}")

    def add_template(
        self,
        fn: t.Callable[..., t.Any],
        uri_template: str,
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        mime_type: str | None = None,
    ) -> ResourceTemplate:
        template = DiscordMCPResourceTemplate.from_function(
            fn,
            uri_template=uri_template,
            name=name,
            title=title,
            description=description,
            mime_type=mime_type,
        )
        self._templates[template.uri_template] = template
        return template
