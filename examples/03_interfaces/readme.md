# Interfaces for data exchange
It is possible use different interfaces for the data exchange:
- FIWARE-API
- MQTT
- File

## FIWARE-API
Data exchange with the data platform of the N5GEH / FIWARE platform using the following APIs
- Contextbroker Orion
    - retrieve the existing entities and attributes as well as the current data of each entity 
    - return the output (attributes / commands) 
- Time Series Database CrateDB
    - query time series
    - use more stable than FIWARE-GE Quantumleap

- The base service uses the [FiLiP](https://github.com/RWTH-EBC/FiLiP/tree/master/examples) Python library and standard FIWARE APIs. It is possible to connect to platforms with or without authentication, you need to adjust the environment variables.

## MQTT
#TODO
## File
Data exchange with via local file.
- Read input data from a file (Note: only `.csv` is supported currently)
    - Read values for the actual (simulation) time of configured input from file
    - csv characteristics:
        - Name column of time = "Time"
        - csv separator = ";"
        - decimal= ","
    - Column name (specific input) in `.csv` must be the like `${Attribute-id_interface}` from the config (Important: the IDs of the attributes `id_interface` over the the interface "file" must therefore be unique)
    - An example of this input is attached as [csv_interface_example.csv](./csv_interface_example.csv), using the the configuration from [n5geh.encodapy/examples/01_config/config.json](./../01_config/config.json)
- Write data to a results file (`.json`)
    - send results of the service to file (for each entity) and timestemp
 
nessesary ENV's with example:
```
PATH_OF_INPUT_FILE = "../validation_data.csv"
START_TIME_FILE = "01.01.2023 06:00"
TIME_FORMAT_FILE = "%d.%m.%Y %H:%M"
```
