"""
Main file so start the example service
"""
import asyncio
from thermal_storage_service import ThermalStorageService
from service_main.main import main

if __name__ == "__main__":
    asyncio.run(main(service_class=ThermalStorageService))
