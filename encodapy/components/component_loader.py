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

def check_component_type(component_type:str):
    """
    Check the component type and return the component type and path.
    If the component type is not fully qualified, return None for the path.
    """
    if "." not in component_type:
        return component_type, None

    component_type_name = component_type.rsplit(".", 1)[-1]
    component_type_path = ".".join([p.strip(".") for p in (component_type, component_type_name)])
    return component_type_name, component_type_path

def get_component_model(component_type: str,
                        model_type: Optional[ModelTypes],
                        model_subname: Optional[str] = None,
                        module_base_path: Optional[str] = None,
                        none_allowed:bool = False,
                        ) -> Union[
                            Type["BaseModel"],
                            Type["BasicComponent"],
                            Type[Enum],
                            None
                        ]:
    """
    Function to get the model information for the component.

    Args:
        component_type (str): Type of the component
        module_path (Optional[str], optional): Path to the module, \
            if not part of EnCoDaPy. Defaults to None.

    Returns:
        Union[Type["BaseModel"], Type["BasicComponent"], Type[Enum], None]: \
            The model if found
    """
    if module_base_path is None:
        module_base_path = f"encodapy.components.{component_type}.{component_type}"

    if model_type is ModelTypes.COMPONENT:
        module_path = module_base_path
    elif model_type is ModelTypes.COMPONENT_CONFIG:
        module_path = f"{module_base_path}_config"
    else:
        raise ValueError(f"Unknown model type: {model_type}")

    config_module = importlib.import_module(module_path)
    model_name = "".join(part.capitalize() for part in component_type.split("_"))

    model_name = model_name if model_subname is None else f"{model_name}{model_subname}"

    try:
        class_model = getattr(config_module, model_name)
        return class_model
    except AttributeError:
        error_msg = f"Class model '{model_name}' not found in {config_module.__name__}"
        if none_allowed:
            logger.debug(error_msg)
            return None
        logger.error(error_msg)
    raise AttributeError(error_msg)



def get_component_class_model(component_type: str,
                              module_path: Optional[str] = None,
                              )-> "Type[BasicComponent]":
    """Get the component class model for a specific component type.

    Args:
        component_type (str): Type of the component
        module_path (Optional[str], optional): Path to the module. \
            Required if not part of EnCoDaPy. Defaults to None.

    Returns:
        Type[BasicComponent]: The component class model
    """
    module = importlib.import_module("encodapy.components.basic_component")
    basic_component_class = getattr(module, "BasicComponent")

    component_type, module_path = check_component_type(component_type)
    component_class = get_component_model(
        component_type = component_type,
        module_base_path = module_path,
        model_type = ModelTypes.COMPONENT)

    if component_class is None:
        raise KeyError(f"Component class not found for {component_type}")
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
        Type[BaseModel]: The component model with the model subname
    """
    component_type, module_path = check_component_type(component_type)
    component_config_model = get_component_model(
        component_type = component_type,
        model_subname = model_subname,
        module_base_path = module_path,
        model_type = ModelTypes.COMPONENT_CONFIG)

    if component_config_model is None:
        raise KeyError(f"Component Config Model not found for {component_type}")

    if issubclass(component_config_model, BaseModel):
        return component_config_model


    error_msg = f"Component class {component_config_model.__name__} is not a subclass of BaseModel"
    logger.error(error_msg)
    raise TypeError(error_msg)

def get_component_static_data_model(component_type: str,
                                    model_subname: str,
                                    module_path: Optional[str] = None,
                                    )-> Union[Type[Enum], None]:
    """Get the component static data model for a specific component type.

    Args:
        component_type (str): Type of the component
        model_name (Optional[str], optional): Name of the Type of the model.
        module_path (Optional[str], optional): Path to the module. \
            Required if not part of EnCoDaPy. Defaults to None.

    Returns:
        Union[Type[BasicComponent], None]: The component static data model or None, if not found.
    """
    component_type, module_path = check_component_type(component_type)
    component_config_model = get_component_model(
        component_type = component_type,
        model_subname = model_subname,
        module_base_path = module_path,
        model_type = ModelTypes.COMPONENT_CONFIG,
        none_allowed=True)

    if component_config_model is None:
        return None

    if issubclass(component_config_model, Enum):
        return component_config_model


    error_msg = f"Component class {component_config_model.__name__} is not a subclass of Enum"
    logger.error(error_msg)
    raise TypeError(error_msg)
