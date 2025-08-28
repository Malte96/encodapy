from pydantic import Field

from encodapy.components.basic_component_config import (
    InputModel,
    IOAllocationModel,
    OutputModel,
)


class NewComponentInputModel(InputModel):
    """
    Input model for the new component
    """

    input: IOAllocationModel = Field(
        ...,
        description="Input of the new component",
        json_schema_extra={"default": "$default_value", "unit": "$unit_value"},
    )


class NewComponentOutputModel(OutputModel):
    """
    Output model for the new component
    """

    result: IOAllocationModel = Field(
        ...,
        description="Result of the new component",
        json_schema_extra={"calculation": "$funtion_name_to_get_the_result"},
    )
