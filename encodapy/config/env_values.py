"""
This module contains the environment variables for the communication interfaces.
Authors: Martin Altenburger, Paul Seidel, Maximilian Beyer
more information: https://docs.pydantic.dev/latest/concepts/pydantic_settings/#usage
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AnyHttpUrl

class FiwareEnvVariables(BaseSettings):
    """
    Environment variables for FIWARE communication.
    They are automatically loaded from the environment or a .env file.

    Environment variables always have the prefix `FIWARE_`.
    """

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_prefix="FIWARE_",
        case_sensitive=False)

    auth: bool = Field(
        default=False,
        description="Enables authentication for FIWARE requests",
    )
    client_id: Optional[str] = Field(
        default=None,
        description="Client ID for FIWARE authentication"
    )
    client_pw: Optional[str] = Field(
        default=None,
        description="Client password for FIWARE authentication"
    )
    token_url: Optional[AnyHttpUrl] = Field(
        default=None,
        description="Token URL for FIWARE authentication"
    )
    baerer_token: Optional[str] = Field(
        default=None,
        description="Bearer token for FIWARE authentication"
    )
    cb_url: Optional[AnyHttpUrl] = Field(
        default=AnyHttpUrl("http://localhost:1026"),
        description="URL of the Context Broker (e.g., Orion-LD)",
    )
    service: str = Field(
        ...,
        description="FIWARE Service header for tenant isolation"
    )
    service_path: str = Field(
        default="/",
        description="FIWARE Service Path for sub-tenant isolation"
    )

    crate_db_url: AnyHttpUrl = Field(
        default=AnyHttpUrl("http://localhost:4200"),
        description="URL of the CrateDB instance",
    )
    crate_db_user: str = Field(
        default="crate",
        description="Username for CrateDB"
    )
    crate_db_pw: str = Field(
        default="",
        description="Password for CrateDB (empty = no authentication)"
    )
    crate_db_ssl: bool = Field(
        default=False,
        description="Enables SSL for the connection to CrateDB"
    )
