"""Text authorship defaults to Host; external composition requires explicit choice."""
from urllib.parse import urlsplit
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


AuthorRole = Literal["canon", "direction", "professional"]


class TextCompositionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Current creative phase is Host-authored. MODEL requires explicit opt-in.
    authorship: Literal["HOST", "MODEL"] = "HOST"
    canon_authorship: Literal["HOST", "MODEL"] | None = None
    direction_authorship: Literal["HOST", "MODEL"] | None = None
    professional_authorship: Literal["HOST", "MODEL"] | None = None
    stream: bool = False
    provider: str = ""
    base_url: str = ""
    canon_model: str = ""
    direction_model: str = ""
    professional_model: str = ""
    api_key: SecretStr | None = Field(default=None, repr=False)
    timeout_seconds: float = Field(default=120, gt=0, le=1800)
    # Provider-specific max_tokens ceiling, not a portable total-cost cap:
    # some APIs meter reasoning separately. Budgeting must include that usage.
    max_output_tokens: int = Field(default=8192, ge=512, le=393216)
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] | None = None

    @model_validator(mode="after")
    def safe_endpoint(self) -> Self:
        if self.base_url:
            u = urlsplit(self.base_url)
            if (u.scheme != "https" or not u.hostname or u.username or u.password
                    or u.query or u.fragment):
                raise ValueError("Author endpoint must be an explicit HTTPS API base URL")
        return self

    @property
    def configured(self) -> bool:
        return bool(self.provider.strip() and self.base_url.strip()
                    and self.api_key and self.api_key.get_secret_value().strip())

    def model_for(self, role: AuthorRole) -> str:
        return {"canon": self.canon_model, "direction": self.direction_model,
                "professional": self.professional_model}[role]

    def authorship_for(self, role: AuthorRole) -> Literal["HOST", "MODEL"]:
        return getattr(self, role + "_authorship") or self.authorship

    def available(self, role: AuthorRole) -> bool:
        return self.authorship_for(role) == "HOST" or self.configured and bool(self.model_for(role).strip())
