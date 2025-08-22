"""
Description: This module provides functions to load component models and configurations.
Author: Martin Altenburger
"""
from typing import TYPE_CHECKING, Optional, Union, Type, cast
import importlib
from enum import Enum
from loguru import logger
from pydantic import BaseModel

if TYPE_CHECKING:
    from encodapy.components.basic_component import BasicComponent

class ModelTypes(Enum):
    """
    Enumeration of model types for components.
    """
    COMPONENT = "component"
    COMPONENT_CONFIG = "component_config"

def get_component_model(component_type: str,
                        model_type: Optional[ModelTypes],
                        model_subname: Optional[str] = None,
                        module_path: Optional[str] = None
                        ) -> Union[Type["BaseModel"], Type["BasicComponent"], Type[Enum]]:
    """
    Function to get the model information for the component.

    Args:
        component_type (str): Type of the component
        module_path (Optional[str], optional): Path to the module, \
            if not part of EnCoDaPy. Defaults to None.

    Returns:
        Tuple[ModuleType, str]: The config module and model name
    """
    if model_type is ModelTypes.COMPONENT:
        module_path = f"encodapy.components.{component_type}.{component_type}"
    elif model_type is ModelTypes.COMPONENT_CONFIG:
        module_path = f"encodapy.components.{component_type}.{component_type}_config"
    else:
        raise ValueError(f"Unknown model type: {model_type}")

    config_module = importlib.import_module(module_path)
    model_name = "".join(part.capitalize() for part in component_type.split("_"))

    model_name = model_name if model_subname is None else f"{model_name}{model_subname}"

    try:
        class_model = getattr(config_module, model_name)
    except AttributeError:
        error_msg = f"Input or output model not found in {config_module.__name__}"
        logger.error(error_msg)
        raise

    return class_model

def get_component_class_model(component_type: str,
                              module_path: Optional[str] = None,
                              )-> "Type[BasicComponent]":
    """Get the component class model for a specific component type.

    Args:
        component_type (str): Type of the component
        module_path (Optional[str], optional): Path to the module. \
            Required if not part of EnCoDaPy. Defaults to None.

    Returns:
        Type[BasicComponent]: _description_
    """
    module = importlib.import_module("encodapy.components.basic_component")
    basic_component_class = getattr(module, "BasicComponent")

    component_class = get_component_model(
        component_type = component_type,
        module_path = module_path,
        model_type = ModelTypes.COMPONENT)

    if issubclass(component_class, basic_component_class):
        return cast("Type[BasicComponent]", component_class)

    error_msg = f"Component class {component_class.__name__} is not a subclass of BasicComponent"
    logger.error(error_msg)
    raise TypeError(error_msg)

def get_component_io_model(component_type: str,
                           model_subname: str,
                           module_path: Optional[str] = None,
                           )-> Type[BaseModel]:
    """Get the component io (input or output) model for a specific component type.

    Args:
        component_type (str): Type of the component
        model_name (Optional[str], optional): Name of the Type of the model.
        module_path (Optional[str], optional): Path to the module. \
            Required if not part of EnCoDaPy. Defaults to None.

    Returns:
        Type[BasicComponent]: _description_
    """

    component_config_model = get_component_model(
        component_type = component_type,
        model_subname = model_subname,
        module_path = module_path,
        model_type = ModelTypes.COMPONENT_CONFIG)

    if issubclass(component_config_model, BaseModel):
        return component_config_model


    error_msg = f"Component class {component_config_model.__name__} is not a subclass of BaseModel"
    logger.error(error_msg)
    raise TypeError(error_msg)

def get_component_static_data_model(component_type: str,
                                    model_subname: str,
                                    module_path: Optional[str] = None,
                                    )-> Type[Enum]:
    """Get the component static data model for a specific component type.

    Args:
        component_type (str): Type of the component
        model_name (Optional[str], optional): Name of the Type of the model.
        module_path (Optional[str], optional): Path to the module. \
            Required if not part of EnCoDaPy. Defaults to None.

    Returns:
        Type[BasicComponent]: _description_
    """

    component_config_model = get_component_model(
        component_type = component_type,
        model_subname = model_subname,
        module_path = module_path,
        model_type = ModelTypes.COMPONENT_CONFIG)

    if issubclass(component_config_model, Enum):
        return component_config_model


    error_msg = f"Component class {component_config_model.__name__} is not a subclass of Enum"
    logger.error(error_msg)
    raise TypeError(error_msg)
