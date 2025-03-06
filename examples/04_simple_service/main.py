"""
Main file so start the example service
"""
import asyncio
from asyncio.tasks import sleep

from example_service import ExampleService


async def main():
    """
    Main function to start the example service
        - prepare the start of the service
        - start the calibration
        - start the health check
        - start the service
    """

    service = ExampleService()

    await service.prepare_start()
    task_calibration = asyncio.create_task(service.start_calibration())
    task_check_health = asyncio.create_task(service.check_health_status())
    task_start_service = asyncio.create_task(service.start_service())

    await asyncio.gather(task_calibration, task_check_health, task_start_service)

    while True:
        await sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
