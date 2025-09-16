# Example 08: Create a New Component

## Overview

This example demonstrates how to create and integrate a new component into the `EnCoDaPy` framework. The new component is defined in the `new_component` module and includes its configuration, input, and output models. The example also shows how to use the `ComponentRunnerService` to run the component.

## Prerequisites

Before running this example, ensure you have the following:

- Python environment set up with all dependencies installed.
- A `.env` file in the root directory with the possibly necessary environment variables.

## Environment Variables

As this example component is configured using the MQTT interface, the environment variables that could be required for this example can be found in [example 05](./../05_simple_service_mqtt/).

## Structure

The example consists of the following files:

- [new_component.py](./new_component/new_component.py): Defines the NewComponent class. (Note the CamelCase notation of the class)
- [new_component_config.py](./new_component/new_component_config.py): Defines the configuration, input, and output models for the new component.
- [config.json](./new_component/config.json): Example configuration for the service, including the new component.
- [main.py](main.py): Entry point to run the example service.

## Usage

Ensure the .env file is correctly configured.

Run the example using the following command:

```bash
python main.py
```
