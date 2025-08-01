# Component Architecture of `encodapy`

## Structure of the Component Code

This module provides a structured way to define and manage components for use within the `encodapy` framework.

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
  An example can be found under:  
  [`examples/06_thermal_storage_service`](../../examples/06_thermal_storage_service/)

---

## Component Configuration

Component configuration must be customized per use case. It is recommended to validate the configuration during component initialization.

### Shared Configuration Elements

Common configuration elements used across multiple components can be placed in:  
`encodapy.components.components_basic_config`

#### `IOAllocationModel`

Defines how inputs and outputs of a component are mapped to specific entities and attributes.

The expected format for each input or output within the `controller_components` configuration is:

```json
{
  "input_or_output_variable": {
    "entity": "entity_id",
    "attribute": "attribute_id"
  }
}
```

This structure is formalized and can be validated using Pydantic.

### Example Configuration

An example of how a Pydantic model can be used to validate the configuration of a component is available at:  
[`encodapy/components/thermal_storage/thermal_storage_config.py`](./thermal_storage/thermal_storage_config.py)

---

## Implementing a New Component

### Each New Component

- Inherits from `BasicComponent`
- Automatically gains:
  - Configuration parsing
  - Input discovery logic (to be triggered by the service)

### Example Constructor

When implementing a new component, begin by initializing the base class:

```python
def __init__(self,
             config: Union[ControllerComponentModel, list[ControllerComponentModel]],
             component_id: str
             ) -> None:

    super().__init__(config=config,
                     component_id=component_id)

    # Component-specific initialization logic
```

**Important**: The `component_id` must match a key in the provided configuration.  
If not, the component will raise a `ValueError` during initialization.