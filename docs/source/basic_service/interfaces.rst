Communication Interfaces
=========================

Configuration of the FIWARE Interface
-------------------------------------
The FIWARE Interface allows communication with FIWARE-based systems using the NGSI standard.
For details about the Usage of FIWARE see `N5GEH <https://github.com/N5GEH/n5geh.tutorials.from_sensor_to_application>`_
or the FIWARE `openapi documentation <https://github.com/FIWARE/specifications>`_.
Until now, only NGSI v2 is supported.

You need to configure some general settings via environment variables as described in :doc:`../readme`. The following information is required for the FIWARE Interface configuration:

.. autopydantic_settings:: encodapy.config.env_values.FiwareEnvVariables


Configuration of the MQTT Interface
------------------------------------

Configuration of the File Interface
------------------------------------

The File Interface allows reading from and writing to data files. The configuration model for the File Interface is defined in the `DataFile`, `DataFileEntity`, and `DataFileAttribute` classes.

You need also to configure some general settings via environment variables as described in :doc:`../readme`.

.. autopydantic_model:: encodapy.config.models.DataFile


.. autopydantic_model:: encodapy.config.models.DataFileEntity


.. autopydantic_model:: encodapy.config.models.DataFileAttribute
