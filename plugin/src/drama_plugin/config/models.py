from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class ServiceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_url: str = ""
    timeout_seconds: float = Field(default=10.0, gt=0)
    api_token: str | None = Field(default=None, repr=False)
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

    memory: DomainProviderConfig = DomainProviderConfig()
    asset: DomainProviderConfig = DomainProviderConfig()
    research: DomainProviderConfig = DomainProviderConfig()
    production: DomainProviderConfig = DomainProviderConfig()
    media: DomainProviderConfig = DomainProviderConfig()
    context: ContextProviderConfig = ContextProviderConfig()
    voice: DomainProviderConfig = DomainProviderConfig()


class RoleDubbingServiceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_url: str = "https://api.fish.audio"
    api_key: SecretStr | None = Field(default=None, repr=False)
    tts_model: Literal["s2-pro"] = "s2-pro"
    timeout_seconds: float = Field(default=120.0, gt=0)
    max_transient_retries: int = Field(default=1, ge=0, le=2)
    output_directory: str = ""


class ServicesConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory: ServiceConfig = ServiceConfig()
    asset: ServiceConfig = ServiceConfig()
    research: ServiceConfig = ServiceConfig()
    production: ServiceConfig = ServiceConfig(timeout_seconds=30.0)
    media: ServiceConfig = ServiceConfig()
    context: ServiceConfig = ServiceConfig(timeout_seconds=30.0)
    voice: ServiceConfig = ServiceConfig()
    role_dubbing: RoleDubbingServiceConfig = RoleDubbingServiceConfig()


class DramaPluginConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plugin: PluginIdentityConfig = PluginIdentityConfig()
    providers: ProvidersConfig = ProvidersConfig()
    services: ServicesConfig = ServicesConfig()
