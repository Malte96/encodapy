# "EnCoDaPy" – Energy Control and Data Preparation in Python.

## Basics
- The Basic Controller provides a system for 
    - read a configuration
    - receive data
    - start a calculation
    - return the results
- This interaction is possible with several interfaces, see [examples/03_interfaces](./examples/03_interfaces/):
    - FIWARE-API
    - MQTT
    - File
- The controller has the functionality to read a configuration from JSON and ENV, validate it and return it as a model.

## Configuration
- The configuration of the service must be provided via `config.json` and has several sections (see the [examples](#examples)):
    - `name`: Controller name - for documentation purposes only
    - `interfaces`: Indicates which interfaces are active
    - `inputs`: Configuration of the inputs to the controller
    - `outputs`: Configuration of the outputs
    - `staticdata`: Static data point configuration (Data that is not continuously updated)
    - `controller_components`: Configuration of the controller components
    - `controller_settings`: General settings about the controller 

- ENVs are required to configure the interfaces / get the config with the default value [`default`]:
    ```
    CONFIG_PATH =  ["./config.json"]
    LOG_LEVEL = 

    # FIWARE - Interface
    CB_URL = ["http://localhost:1026"]
    FIWARE_SERVICE = ["service"]
    FIWARE_SERVICE_PATH = [/]
    FIWARE_AUTH = [False]
    # only used if FIWARE_AUTH = true / Option 1 for authentication
    FIWARE_CLIENT_ID = 
    FIWARE_CLIENT_PW = 
    FIWARE_TOKEN_URL = 
    # only used if FIWARE_AUTH = true and the three previously not set / Option 2 for authentication
    FIWARE_BAERER_TOKEN = []

    CRATE_DB_URL = ["http://localhost:4200"]
    CRATE_DB_USER = ["crate"]
    CRATE_DB_PW = [""]
    CRATE_DB_SSL = [False]

    # FILE - Interface
    PATH_OF_INPUT_FILE = "path_to_the_file_\\validation_data.csv"
    START_TIME_FILE = "01.01.2023 06:00"
    TIME_FORMAT_FILE = "%d.%m.%Y %H:%M" - format of time in file
    ```

## Usage

To create your own custom service, you have to overwrite two functions of the [ControllerBasicService](./../../encodapy/service/basic_service.py):
- `calculation()`: Asynchronous function to perform the main calculation in the service
- `calibration()`: Asynchrone function to calibrate the service or coefficients in the service if required

To start the service, you need to call
- `prepare_start()`: To prepare the start of the service
- `start_calibration()`: To start the calibration if required
- `start_service()`: To start the service

A easy posibility to start the service is to run the base [main.py](./service_main/main.py). For more details, see the [examples](#examples)

### Examples
For different examples and documentation, how to use the tool - see [examples](./examples/).

The examples are intended to help you use the tool and understand how it works:
- the configuration
- the use

### Units
- Inputs and outputs get information about the unit. The class [`DataUnits`](./controller_software/utils/units.py) is used for this.
- More units must be added manually.
- Timeranges:
    - Timeranges for data queries are different for calculation and calibration.
    - The following timeranges are possible
        - '"minute"'
        - '"hour"'
        - '"day"'
        - '"month"' --> 30 days
- Today, there ist no adjustment for different units. Its a TODO for the future

### Deployment
The recommended way to run the service is:
- Create a Python environment using Poetry (see [pyproject.toml](./pyproject.toml)).
- Use a Docker container for production deployments (create a custom image using the [dockerfile](dockerfile)).
