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
#TODO
