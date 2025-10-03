from __future__ import annotations

import inspect
import logging
import re
import typing as t

import pydantic_core
from mcp.server.fastmcp.resources import FunctionResource, ResourceManager, ResourceTemplate
from mcp.server.fastmcp.resources.base import Resource
from mcp.types import Icon
from pydantic import AnyUrl

from discord_mcp.core.server.shared.context import DiscordMCPContext, get_context
from discord_mcp.utils.checks import context_safe_validate_call, find_kwarg_by_type
from discord_mcp.utils.converters import get_cached_typeadapter, process_callable_result, prune_param
from discord_mcp.utils.exceptions import ResourceReadError

if t.TYPE_CHECKING:
    from mcp.server.fastmcp.server import Context
    from mcp.server.session import ServerSessionT
    from mcp.shared.context import LifespanContextT, RequestT


__all__: tuple[str, ...] = (
    "DiscordMCPResourceManager",
    "DiscordMCPFunctionResource",
)


logger = logging.getLogger(__name__)


class DiscordMCPFunctionResource(FunctionResource):
    async def read(self) -> str | bytes:
        """Read the resource by calling the wrapped function."""
        try:
            # First layer calls a dummy function to ensure, input validation is done,
            # and then calls the actual function with the context if requirements meet
            context_kwarg = find_kwarg_by_type(self.fn, DiscordMCPContext)
            params = {} if not context_kwarg else {context_kwarg: get_context()}

            result = await process_callable_result(self.fn, params)

            if isinstance(result, Resource):
                return await result.read()
            elif isinstance(result, (str, bytes)):
                return result
            else:
                return pydantic_core.to_json(result, fallback=str, indent=2).decode()
        except Exception as e:
            raise ResourceReadError(f"Error reading resource {self.uri}: {e}")

    @classmethod
    def from_function(
        cls,
        fn: t.Callable[..., t.Any],
        uri: str,
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        mime_type: str | None = None,
        icons: list[Icon] | None = None,
    ) -> "FunctionResource":
        """Create a FunctionResource from a function."""
        func_name = name or fn.__name__
        if func_name == "<lambda>":
            raise ValueError("You must provide a name for lambda functions")

        # Create a dummy sync function, from callback signature for input validation
        validated_fn = context_safe_validate_call(fn)

        return cls(
            uri=AnyUrl(uri),
            name=func_name,
            title=title,
            description=description or fn.__doc__ or "",
            mime_type=mime_type or "text/plain",
            fn=validated_fn,
            icons=icons,
        )


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
        icons: list[Icon] | None = None,
        context_kwarg: str | None = None,
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

        context_kwarg = context_kwarg or find_kwarg_by_type(fn, DiscordMCPContext)

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

        # Create a dummy sync function, from callback signature for input validation
        validated_fn = context_safe_validate_call(fn)

        return cls(
            uri_template=uri_template,
            name=func_name,
            title=title,
            description=description,
            mime_type=mime_type or "text/plain",
            fn=validated_fn,
            parameters=parameters,
            icons=icons,
            context_kwarg=context_kwarg,
        )

    async def create_resource(
        self,
        uri: str,
        params: dict[str, t.Any],
        context: Context[ServerSessionT, LifespanContextT, RequestT] | None = None,
    ) -> Resource:
        try:
            # First layer calls a dummy function to ensure, input validation is done,
            # and then calls the actual function with the context if requirements meet
            result = await process_callable_result(self.fn, params)

            return DiscordMCPFunctionResource(
                uri=uri,  # type: ignore
                name=self.name,
                title=self.title,
                description=self.description,
                mime_type=self.mime_type,
                fn=lambda: result,
            )
        except Exception as e:
            raise ValueError(f"Error creating resource from template: {e}")


class DiscordMCPResourceManager(ResourceManager):
    async def get_resource(
        self, uri: AnyUrl | str, context: Context[ServerSessionT, LifespanContextT, RequestT] | None = None
    ) -> Resource | None:
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
                    context_kwarg = template.context_kwarg or find_kwarg_by_type(template.fn, DiscordMCPContext)
                    params |= {context_kwarg: context or get_context()} if context_kwarg else {}
                    return await template.create_resource(uri_str, params, context=context)
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
        icons: list[Icon] | None = None,
    ) -> ResourceTemplate:
        template = DiscordMCPResourceTemplate.from_function(
            fn,
            uri_template=uri_template,
            name=name,
            title=title,
            description=description,
            mime_type=mime_type,
            icons=icons,
        )
        self._templates[template.uri_template] = template
        return template
