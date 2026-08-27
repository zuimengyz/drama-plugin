from typing import Literal


SpeechRejectionReason = Literal[
    "VOICE_MODEL_INCOMPATIBLE",
    "INVALID_REQUEST",
    "UNSUPPORTED_PARAMETER",
    "AUTH_OR_PERMISSION",
    "QUOTA_OR_ACCOUNT",
    "CONTENT_REJECTED",
    "UNKNOWN_REJECTION",
]


class DramaPluginError(Exception):
    """Base error for all expected plugin failures."""


class ConfigurationError(DramaPluginError):
    """Configuration or manifest is invalid."""


class SkillLoadError(DramaPluginError):
    """A skill could not be discovered or validated."""


class ToolNotFoundError(DramaPluginError):
    """A requested tool code is not registered."""


class DuplicateToolError(DramaPluginError):
    """A tool code is already registered."""


class ProviderError(DramaPluginError):
    """A provider could not satisfy a domain operation."""


class SpeechProviderError(ProviderError):
    """A speech provider rejected or could not complete a request safely."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool = False,
        provider_error_code: str | None = None,
        provider_error_message: str | None = None,
        provider_request_id: str | None = None,
        rejection_reason: SpeechRejectionReason | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable
        self.provider_error_code = provider_error_code
        self.provider_error_message = provider_error_message
        self.provider_request_id = provider_request_id
        self.rejection_reason = rejection_reason


class ProviderResultUnknown(SpeechProviderError):
    """Submission may have succeeded, so an automatic paid retry is unsafe."""


class MediaImportSourceError(ProviderError):
    """An external media source is unsafe or cannot be streamed."""

    def __init__(self, message: str, *, error_code: str) -> None:
        super().__init__(message)
        self.error_code = error_code


class RemoteServiceError(ProviderError):
    """A remote service returned an error or invalid payload."""

    def __init__(self, message: str, *, status_code: int | None = None, error_code: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class ContextBuildError(DramaPluginError):
    """A domain context projection failed."""


class ContractValidationError(DramaPluginError):
    """A payload does not satisfy a domain contract."""
