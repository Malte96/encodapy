# System Controller

## Basics
- The Basic Controller provides a system for 
    - read a configuration
    - receive data
    - start a calculation
    - return the results
- This interaction is possible with several interfaces.
- The controller has the functionality to read a configuration from JSON and ENV, validate it and return it as a model.

## Configuration
- The config has several sections:
    - Interfaces: Indicates which interfaces are active
    - Inputs': Configuration of the inputs to the controller
    - Outputs: Configuration of the outputs
    - metadata # TODO
    - controller_components: Configuration of the controller components
    - controller_settings: General settings about the controller 

- ENVs are required to configure the interfaces / get the config with the default value [`default`]:
    ```
    CONFIG_PATH =  ["./config.json"]
    LOG_LEVEL = 

    # FIWARE - Interface
    CB_URL = ["http://localhost:1026"]
    FIWARE_SERVICE = ["service"]
    FIWARE_SERVICE_PATH = [/]
    FIWARE_AUTH = [False]
    # only used if FIWARE_AUTH = true    
    FIWARE_CLIENT_ID = 
    FIWARE_CLIENT_PW = 
    FIWARE_TOKEN_URL = 
    # only used if FIWARE_AUTH = true and the three previously not set
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

### Units
- Inputs and outputs get information about the unit. The class [`DataUnits`](./controller_software/utils/units.py) is used for this.
- Timeranges:
    - Timeranges for data queries are different for calculation and calibration.
    - The following timeranges are possible
        - '"minute"'
        - '"hour"'
        - '"day"'
        - '"month"' --> 30 days
- TODO: Implement the adjustment for different units.

## Examples
- [config.ipynb](./examples/config.ipynb): Shows a example how the config could be used
