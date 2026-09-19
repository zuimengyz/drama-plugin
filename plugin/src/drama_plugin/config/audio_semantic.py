"""Optional observation provider configuration; no creative defaults."""
from typing import Literal, Self
from urllib.parse import urlsplit
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


class AudioSemanticProviderConfig(BaseModel):
    model_config = ConfigDict(extra='forbid', hide_input_in_errors=True)
    mode: Literal['off', 'bailian_qwen_omni'] = 'off'


class QwenOmniConfig(BaseModel):
    model_config = ConfigDict(extra='forbid', hide_input_in_errors=True)
    api_key: SecretStr | None = Field(default=None, repr=False, exclude=True)
    base_url: str = Field(default='', repr=False)
    model: str = 'qwen3.8-omni-flash'
    reasoning_effort: Literal['none','minimal','low','medium','high','xhigh','max'] = 'none'
    use_multichannel: bool = False
    timeout_seconds: float = Field(default=120, gt=0, le=300)
    max_transient_retries: int = Field(default=2, ge=0, le=2)

    @model_validator(mode='after')
    def safe_url(self) -> Self:
        if self.api_key and any(ch.isspace() or ord(ch) < 32 for ch in self.api_key.get_secret_value()):
            raise ValueError('Audio semantic API key contains unsupported whitespace/control characters')
        if self.base_url:
            url = urlsplit(self.base_url)
            if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment:
                raise ValueError('Audio semantic endpoint requires HTTPS without credentials/query/fragment')
        if not self.model.strip():
            raise ValueError('Audio semantic model cannot be empty')
        return self
