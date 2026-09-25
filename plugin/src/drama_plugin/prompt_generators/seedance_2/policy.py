"""Adapted knowledge provenance. This is data, not an installed external Skill."""
import json
from pathlib import Path
from typing import Any
from drama_plugin.contracts.base import sha256_canonical


def policy() -> dict[str, Any]:
    data = json.loads(Path(__file__).with_name('policy.json').read_text())
    return {**data, 'policy_hash': sha256_canonical(data)}
