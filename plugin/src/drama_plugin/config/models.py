from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, SecretStr, PrivateAttr, field_validator, model_validator
from drama_plugin.config.audio_semantic import AudioSemanticProviderConfig, QwenOmniConfig

from drama_plugin.config.video_route import VideoRoutePolicy


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
    audio_semantic: AudioSemanticProviderConfig = AudioSemanticProviderConfig()


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
    qwen_omni: QwenOmniConfig = QwenOmniConfig()


class DramaPluginConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    character_repository_root: str = ""

    video_route_policy: VideoRoutePolicy = Field(default_factory=VideoRoutePolicy)
    rhythm_speed: Literal["work_defined", "slow", "medium", "fast"] = "work_defined"
    _rhythm_source: str = PrivateAttr(default="default:work_defined")

    @field_validator("rhythm_speed", mode="before")
    @classmethod
    def trim_rhythm(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @property
    def rhythm_source(self) -> str:
        return self._rhythm_source

    plugin: PluginIdentityConfig = PluginIdentityConfig()
    providers: ProvidersConfig = ProvidersConfig()
    services: ServicesConfig = ServicesConfig()

    @model_validator(mode='after')
    def optional_audio_semantics(self) -> Self:
        if self.providers.audio_semantic.mode == 'bailian_qwen_omni':
            qwen = self.services.qwen_omni
            if not qwen.api_key or not qwen.api_key.get_secret_value().strip() or not qwen.base_url.strip():
                raise ValueError('MISSING_QWEN_OMNI_RUNTIME_CONFIGURATION: API_KEY and BASE_URL required when enabled')
        return self
