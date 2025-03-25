# Example for usage with a simple mqtt service

- as an preprint for a own description:

<!-- TODO: rewrite everything from here -->

## Overview

As an example of a simple service using Encodapy, a heating regulator based on a two-position regulator is created. The following parts show different aspects of the application:

- [configure_fiware_platform.ipynb](./configure_fiware_platform.ipynb): Notebook to add the needed configuration and values to the fiware platform
- [config.json](./config.json): Configuration for the service - see [01_config](./../01_config/)
- [example_service.py](./example_service.py): Code of the service example
- [main.py](./main.py): Script to start the service
- [run_simple_service.ipynb](./run_simple_service.ipynb): Notebook to run the service (also possible to run the [main.py](./main.py))

To run the example, you need to add a [.env](.env):

```env
FIWARE_IOTA= ["http://localhost:4041"]      # URL of the IoT Agent
FIWARE_CB= ["http://localhost:1026"]        # URL of the Context Broker
FIWARE_SERVICE= ["example_service"]         # Name of the FIWARE Service
FIWARE_SERVICE_PATH= ["/"]                  # FIWARE Service Path, usually "/"
```

It is also necessary to have a running software platform.

## Basics

To create your own custom service, you have to overwrite two functions of the [ControllerBasicService](./../../encodapy/service/basic_service.py):

- `calculation`: Asynchronous function to perform the main calculation in the service
- `calibration`: Asynchrone function to calibrate the service or coefficients in the service if required

For the models of the inputs and outputs see [02_datatransfer](./../02_datatransfer/)
