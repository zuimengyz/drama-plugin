from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ServiceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_url: str = ""
    timeout_seconds: float = Field(default=10.0, gt=0)
    api_token: str | None = None
    operations: dict[str, str] = {}


class PluginIdentityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = "drama-plugin"
    version: str = "0.1.0"


class DomainProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["mock", "http"] = "mock"


class ContextProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["local", "http"] = "local"


class ProvidersConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: DomainProviderConfig = DomainProviderConfig()
    asset: DomainProviderConfig = DomainProviderConfig()
    history: DomainProviderConfig = DomainProviderConfig()
    generation: DomainProviderConfig = DomainProviderConfig()
    media: DomainProviderConfig = DomainProviderConfig()
    context: ContextProviderConfig = ContextProviderConfig()


class ServicesConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: ServiceConfig = ServiceConfig()
    asset: ServiceConfig = ServiceConfig()
    history: ServiceConfig = ServiceConfig()
    generation: ServiceConfig = ServiceConfig(timeout_seconds=30.0)
    media: ServiceConfig = ServiceConfig()
    context: ServiceConfig = ServiceConfig(timeout_seconds=30.0)


class DramaPluginConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plugin: PluginIdentityConfig = PluginIdentityConfig()
    providers: ProvidersConfig = ProvidersConfig()
    services: ServicesConfig = ServicesConfig()
