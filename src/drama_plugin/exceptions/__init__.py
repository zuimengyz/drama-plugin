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


class RemoteServiceError(ProviderError):
    """A remote service returned an error or invalid payload."""


class ContextBuildError(DramaPluginError):
    """A domain context projection failed."""


class ContractValidationError(DramaPluginError):
    """A payload does not satisfy a domain contract."""
