import pydantic

__all__: tuple[str, ...] = ("CallToolResponse",)


class CallToolResponse(pydantic.BaseModel):
    message: str = pydantic.Field(description="Result of the tool call.")
