"""
Main file so start the example service
"""
import asyncio
from asyncio.tasks import sleep

from mqtt_controller import MQTTController


async def main():
    """
    Main function to start the example service
        - prepare the start of the service
        - start the calibration
        - start the service
    """

    service = MQTTController()

    await service.prepare_start()
    task_for_calibration = asyncio.create_task(service.start_calibration())
    task_for_start_service = asyncio.create_task(service.start_service())

    await asyncio.gather(task_for_calibration,
                         task_for_start_service)

    while True:
        await sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
