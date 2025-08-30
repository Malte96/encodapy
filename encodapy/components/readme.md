# Component Architecture of `EnCoDaPy`

## Structure of the Component Code

This module provides a structured way to define and manage components for use within the `EnCoDaPy` framework.

### Highlights

- Custom module for component definitions.
- Components are imported via `__init__.py` to enable simplified access.
- All components inherit from a base component with shared logic and configuration.
- Modular structure improves maintainability and reusability.

### Module Structure

- Component module: `encodapy.components`
- Base component: `encodapy.components.basic_component`
- Base configuration: `encodapy.components.components_basic_config`
- Individual component: `encodapy.components.$Component` (imported via `__init__.py`)

### Available Components

- `ThermalStorage`: Thermal storage component to calculate the stored energy using temperature sensors.  
  An example can be found under: [`examples/06_thermal_storage_service`](../../examples/06_thermal_storage_service/)
- `TwoPointController`: Two-Point-Controller component for the steering of the loading process of a thermal storage or other processes.  
  An example can be found under: [`examples/07_component_runner`](../../examples/07_component_runner/)

---

## Component Configuration

Component configuration must be customized per use case. It is recommended to validate the configuration during component initialization. This structure is formalized and can be validated using Pydantic.

### Shared Configuration Elements

Common configuration elements used across multiple components can be placed in:  
`encodapy.components.components_basic_config`

#### `ControllerComponentModel`

This is a model for configuring components that form part of the general configuration of a service.

#### `IOModell`

Root-Modell to describe the structur of the Inputs, Outputs and static data (`$INPUT_OR_OUTPUT_VARIABLE`) of a component as a dictionary of `IOAllocationModel`, like:

```json

  "inputs": {
    "$INPUT_OR_OUTPUT_VARIABLE_1": IOAllocationModel,
    "$INPUT_OR_OUTPUT_VARIABLE_2": IOAllocationModel
  }

```

#### `IOAllocationModel`

Defines how inputs, outputs and static data of a component are mapped to specific entities and attributes.

The expected format for each input or output (`$INPUT_OR_OUTPUT_VARIABLE`) within the controller components (`controller_components`) configuration is:

```json
{
  "$INPUT_OR_OUTPUT_VARIABLE": {
    "entity": "entity_id",
    "attribute": "attribute_id"
  }
}
```

#### `ControllerComponentStaticData`

A model for storing the static data of a component as a dict of `ControllerComponentStaticDataAttribute` in a Pydantic root model.

#### `ControllerComponentStaticDataAttribute`

Model for the static data attributes of the controller component, is part if the `ControllerComponentStaticData`-Model.

### Example Configuration

An example of how a Pydantic model can be used to validate the configuration of a component is available at:  
[`encodapy/components/thermal_storage/thermal_storage_config.py`](./thermal_storage/thermal_storage_config.py)

---

## Implementing a New Component

- an example is provided in [`examples/08_create_new_component`](../../examples/08_create_new_component)

### Infos for the New Component

- Inherits from `BasicComponent`
- Automatically gains:
  - Configuration parsing
  - Input discovery logic (to be triggered by the service)
  - A function to run the component and calculates all the outputs mentioned in the configuration.

- Each component needs the same structure in a module called `*.$new_component`:
  - `__init__.py`: can be empty
  - `new_component.py`: The Python module that initialises the class `NewComponent`.
  - `new_component_config.py`: The Python module containing all the necessary configurations.

  Make sure the names follow this convention if you want to use the component runner.

### Details to create a New Component

- When implementing a new component, begin by initializing the base class in `NewComponent`:

  ```python
  class NewComponent(BasicComponent):
    """
    Class for a new component
    """

    def __init__(
        self,
        config: Union[ControllerComponentModel, list[ControllerComponentModel]],
        component_id: str,
    ) -> None:
        # Add the necessary instance variables here (you need to store the input data in the component)
        # example: self.variable: Optional[float]

        super().__init__(config=config, component_id=component_id)

        # Component-specific initialization logic
  ```

  **Important**: The `component_id` must match a key in the provided configuration. If not, the component will raise a `ValueError` during initialization.

- The Configuration(`new_component_config.py`) needs as a minimum:
  - `NewComponentInputModel(InputModel)`: A definition of the input datapoints.
  
    You can add information about the default values and units for each input using a `Field` definition with the `json_schema_extra` key:

    ```python
    from pydantic import Field

    from encodapy.components.basic_component_config import IOAllocationModel, InputModel


    class NewComponentInputModel(InputModel):
        """
        Input model for the new component
        """

        input: IOAllocationModel = Field(
            ...,
            description="Input of the new component",
            json_schema_extra={"default": "$default_value", "unit": "$unit_value"},
        )
    ```

    The value of the variable `"$unit_value"` must be a valid unit from the `encodapy.utils.units.DataUnits` such as `"CEL"` for °C.

    These two values will be added to the IOModel of the component.

  - `NewComponentOutputModel(OutputModel)`: A definition of the possible output datapoints / results.

    This BaseModell needs to contain a `Field`-Definition with the key: `json_schema_extra={"calculation": "$funtion_name_to_get_the_result"}`:

    ```python
    from pydantic import Field

    from encodapy.components.basic_component_config import IOAllocationModel, OutputModel


    class NewComponentOutputModel(OutputModel):
        """
        Output model for the new component
        """
  
        result: IOAllocationModel = Field(
            ...,
            description="Result of the new component",
            json_schema_extra={"calculation": "$funtion_name_to_get_the_result"},
        )
    ```

    **If you only want to use some of the possible results, you need to set them to  `Optional[IOAllocationModel]`**

    As with the `NewComponentInputModel`, you could also add information about the unit.
  - `NewComponentStaticData(Enum)`: A Enum class which defines the required static keys to check during the initilisazion. It should look like this:

    ```python
    from enum import Enum

    class NewComponentStaticData(Enum):
        """
        Static data for the new component
        """
        STATIC_VALUE = "$static_value_name"
    ```

    You do not need this definition if you don't want to use static data.
- If the new component requires preparation before the first run, this should be added to the `prepare_component()` function.

- The new component requires in the `new_component.py`:
  - a function to set the necessary inputs. For this, you have to use the function `set_input_values(input_entities: list[InputDataEntityModel])`.
  - the functions to calculate the results with the same names as mentioned in `NewComponentOutputModel(OutputModel)`, using the component's internal value storage and other background functions.
- If the new component requires calibration, you should extend the function `calibrate()`. In the basic component, this function is only used to update static data.

### Using the New Component

- If you are using the structure for a new component, you can specify the module path in your project's configuration as the component type, as shown in the following example:

```json
  ...
  "controller_components": [
      {
          "id": "example_controller",
          "type": "$your_project.$your_modules.$new_component",
          ...
      }
    ]
  ...
```
