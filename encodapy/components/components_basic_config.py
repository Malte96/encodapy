"""
Basic configuration for the components in the Encodapy framework.
Author: Martin Altenburger
"""
from pydantic import BaseModel, Field

class IOAllocationModel(BaseModel):
    """
    Model for the input or output allocation.
    
    Contains:
        `entity`: ID of the entity to which the input or output is allocated
        `attribute`: ID of the attribute to which the input or output is allocated
    """
    entity: str = Field(
        ...,
        description="ID of the entity to which the input or output is allocated")
    attribute: str = Field(
        ...,
        description="ID of the attribute to which the input or output is allocated")
