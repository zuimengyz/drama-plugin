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
