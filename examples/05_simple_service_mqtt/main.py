"""
Main file so start the example service
"""

import asyncio
from mqtt_controller import MQTTController
from service_main.main import main


if __name__ == "__main__":

    asyncio.run(main(service_class=MQTTController))
