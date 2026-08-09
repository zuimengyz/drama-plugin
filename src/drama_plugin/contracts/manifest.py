from __future__ import annotations

from pydantic import Field

from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.context import ContextScope


class ContextCapabilities(ContractModel):
    scopes: list[ContextScope]
    supports_full_context: bool = True
    supports_patch: bool = True


class PluginManifest(ContractModel):
    name: str
    version: str
    description: str
    skills_directory: str
    supported_tool_domains: list[str]
    context_capabilities: ContextCapabilities


class SkillContextSpec(ContractModel):
    required: list[str] = []
    optional: list[str] = []
    refresh_after: list[str] = []


class SkillToolSpec(ContractModel):
    preferred: list[str] = []
    allowed: list[str] = []


class SkillCompletion(ContractModel):
    conditions: list[str] = Field(min_length=1)


class SkillDefinition(ContractModel):
    code: str
    name: str
    description: str
    context: SkillContextSpec
    tools: SkillToolSpec
    completion: SkillCompletion
    instructions: str = ""
