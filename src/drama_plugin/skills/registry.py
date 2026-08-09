from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError

from drama_plugin.contracts.manifest import SkillDefinition
from drama_plugin.exceptions import SkillLoadError


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, SkillDefinition] = {}

    def load_directory(self, skills_directory: Path | str) -> None:
        root = Path(skills_directory)
        if not root.is_dir():
            raise SkillLoadError(f"Skills directory does not exist: {root}")
        for directory in sorted(path for path in root.iterdir() if path.is_dir()):
            config_path = directory / "skill.yaml"
            instructions_path = directory / "SKILL.md"
            if not config_path.exists() or not instructions_path.exists():
                continue
            self.register(self._load_one(config_path, instructions_path))

    def _load_one(self, config_path: Path, instructions_path: Path) -> SkillDefinition:
        try:
            payload: Any = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise SkillLoadError(f"Skill config root must be a mapping: {config_path}")
            payload["instructions"] = instructions_path.read_text(encoding="utf-8")
            definition = SkillDefinition.model_validate(payload)
        except SkillLoadError:
            raise
        except (OSError, yaml.YAMLError, ValidationError) as exc:
            raise SkillLoadError(f"Invalid skill: {config_path}") from exc
        if definition.code != config_path.parent.name:
            raise SkillLoadError(f"Skill code must match directory name: {definition.code}")
        return definition

    def register(self, skill: SkillDefinition) -> None:
        if skill.code in self._skills:
            raise SkillLoadError(f"Duplicate skill code: {skill.code}")
        self._skills[skill.code] = skill

    def get(self, code: str) -> SkillDefinition:
        try:
            return self._skills[code]
        except KeyError as exc:
            raise SkillLoadError(f"Skill not found: {code}") from exc

    def list(self) -> list[SkillDefinition]:
        return sorted(self._skills.values(), key=lambda item: item.code)
