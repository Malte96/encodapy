"""
Main file so start the example service
"""
import asyncio
from example_service import ExampleService
from service_main.main import main

if __name__ == "__main__":
    asyncio.run(main(service_class=ExampleService))
