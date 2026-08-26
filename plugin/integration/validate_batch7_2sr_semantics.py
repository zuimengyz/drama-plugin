from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from drama_plugin.audio.foundation import audio_input_fingerprint
from drama_plugin.contracts.audio import (
    CharacterUnderstanding,
    SceneState,
    SpeechGenerationRequest,
    TargetTimingPolicy,
    VoiceProfile,
)
from drama_plugin.providers.speech.bailian_qwen import (
    compile_bailian_qwen_speech_payload,
    rank_bailian_qwen_voice_candidates,
)


SECTION_ALIASES = {
    "identityLifeStage": "identityAndLifeStage",
    "experience": "experienceStructure",
    "decisionStyle": "decisionStyle",
    "emotionalRegulation": "emotionalRegulation",
    "interaction": "interactionStyle",
    "authorityResponsibility": "authorityAndResponsibility",
    "communication": "communicationStyle",
    "physicalBaseline": "physicalBaseline",
    "presentationModes": "presentationModes",
    "alignmentConstraints": "alignmentAndConstraints",
}
VALUE_SHORTCUTS = ("英雄", "反派", "贤明", "昏庸", "勇敢", "懦弱", "高尚", "卑劣")


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _sha256_json(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _normalize_understanding(raw: dict[str, Any]) -> CharacterUnderstanding:
    sections = raw["sections"]
    source_refs: list[str] = []
    payload: dict[str, Any] = {
        "schemaVersion": raw["schemaVersion"],
        "understandingId": f"character-understanding:{raw['speakerKey']}:7.2s-r",
        "speakerKey": raw["speakerKey"],
    }
    for source_name, contract_name in SECTION_ALIASES.items():
        dimensions = sections.get(source_name, {})
        payload[contract_name] = dimensions
        for dimension in dimensions.values():
            source_refs.extend(dimension.get("evidenceRefs", []))
    unknown_fields: list[str] = []
    for section, fields in raw.get("unknownFields", {}).items():
        unknown_fields.extend(f"{section}.{field}" for field in fields)
    payload["unknownFields"] = sorted(set(unknown_fields))
    payload["sourceRefs"] = sorted(set(source_refs))
    return CharacterUnderstanding.model_validate(payload)


def _normalize_profile(
    raw: dict[str, Any], understanding: CharacterUnderstanding
) -> VoiceProfile:
    speaker_key = raw["speakerKey"]
    return VoiceProfile.model_validate(
        {
            "profileId": f"voice-profile:{speaker_key}:7.2s-r",
            "speakerKey": speaker_key,
            "creativeProfile": raw["creativeProfile"],
            "characterUnderstanding": understanding.model_dump(
                mode="json", by_alias=True
            ),
            "providerMappings": [],
            "nonMaterialMetadata": {
                "voiceBindingStatus": "PENDING",
                "source": "skill-driven-prepaid-preflight",
            },
        }
    )


def _bind_candidate(
    request: SpeechGenerationRequest, candidate: Any
) -> SpeechGenerationRequest:
    profile = request.voice_profile.model_copy(
        update={"provider_mappings": [candidate]}
    )
    payload = request.model_dump(mode="json", by_alias=True)
    payload["voiceProfile"] = profile.model_dump(mode="json", by_alias=True)
    payload["providerMapping"] = candidate.model_dump(mode="json", by_alias=True)
    return SpeechGenerationRequest.model_validate(payload)


def _identity_invariance(
    request: SpeechGenerationRequest, expected_ranking: list[Any]
) -> bool:
    changed = copy.deepcopy(request.model_dump(mode="json", by_alias=True))
    synthetic_key = "speaker:synthetic-renamed"
    changed["speakerKey"] = synthetic_key
    changed["voiceProfile"]["speakerKey"] = synthetic_key
    changed["voiceProfile"]["characterUnderstanding"]["speakerKey"] = synthetic_key
    changed["voiceProfile"]["characterUnderstanding"]["understandingId"] = (
        "character-understanding:synthetic-renamed"
    )
    renamed = SpeechGenerationRequest.model_validate(changed)
    actual = rank_bailian_qwen_voice_candidates(renamed, limit=3)
    expected = [(item.voice_id, item.non_material_metadata) for item in expected_ranking]
    observed = [(item.voice_id, item.non_material_metadata) for item in actual]
    return observed == expected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()

    source = json.loads(args.source.read_text(encoding="utf-8"))
    if source["skillActuallyInvoked"] is not True or source["paidProviderCalls"] != 0:
        raise ValueError("preflight must be Skill-driven and contain zero paid calls")
    if source["fixtureBypass"] is not False:
        raise ValueError("fixture bypass is forbidden")
    if source["gates"] != {
        "contextLoaded": True,
        "characterUnderstandingReady": True,
        "providerNeutral": True,
        "generationAuthorized": False,
    }:
        raise ValueError("prepaid preflight gates are incomplete")
    serialized = json.dumps(source, ensure_ascii=False)
    present_shortcuts = [word for word in VALUE_SHORTCUTS if word in serialized]
    if present_shortcuts:
        raise ValueError(f"value-laden voice shortcuts present: {present_shortcuts}")

    understandings = [
        _normalize_understanding(item) for item in source["characterUnderstandings"]
    ]
    understanding_by_speaker = {item.speaker_key: item for item in understandings}
    profiles = [
        _normalize_profile(item, understanding_by_speaker[item["speakerKey"]])
        for item in source["voiceProfiles"]
    ]
    profile_by_speaker = {item.speaker_key: item for item in profiles}
    states = [SceneState.model_validate(item) for item in source["sceneStates"]]
    state_by_dialogue = {item.spoken_content_id: item for item in states}
    intent_by_dialogue = {
        item["spokenContentId"]: item for item in source["performanceIntents"]
    }
    exact_by_dialogue = {
        item["spokenContentId"]: item for item in source["exactDialogueHashes"]
    }

    requests: list[SpeechGenerationRequest] = []
    candidate_evidence: list[dict[str, Any]] = []
    propagation: list[dict[str, Any]] = []
    for dialogue_id in source["contextIds"]["dialogueIds"]:
        exact = exact_by_dialogue[dialogue_id]
        request = SpeechGenerationRequest(
            work_id=source["contextIds"]["workId"],
            scene_id=source["contextIds"]["sceneId"],
            spoken_content_id=dialogue_id,
            exact_text=exact["exactText"],
            speaker_key=exact["speakerKey"],
            voice_profile=profile_by_speaker[exact["speakerKey"]],
            scene_state=state_by_dialogue[dialogue_id],
            performance_intent=intent_by_dialogue[dialogue_id],
            target_timing_policy=TargetTimingPolicy(policy="NATURAL"),
            non_material_metadata={
                **source["contextIds"],
                "skillCode": source["skillCode"],
                "voiceBindingStatus": "PENDING",
            },
        )
        if hashlib.sha256(request.exact_text.encode("utf-8")).hexdigest() != exact[
            "sha256"
        ]:
            raise ValueError(f"exact Dialogue hash mismatch: {dialogue_id}")
        candidates = rank_bailian_qwen_voice_candidates(request, limit=3)
        if not _identity_invariance(request, candidates):
            raise ValueError(f"candidate ranking depends on speaker identity: {dialogue_id}")
        bound = _bind_candidate(request, candidates[0])
        provider_payload = compile_bailian_qwen_speech_payload(bound)
        instruction = provider_payload["input"].get("instructions", "")
        required_instruction_terms = (
            "长期基础声音",
            "当前场景状态",
            "本句表演变化",
            "不得把高克制解释为低能量",
        )
        if not all(term in instruction for term in required_instruction_terms):
            raise ValueError(f"semantic instruction sections missing: {dialogue_id}")
        ranking = candidates[0].non_material_metadata["candidateRanking"]
        candidate_evidence.append(
            {
                "spokenContentId": dialogue_id,
                "speakerKey": request.speaker_key,
                "strategy": candidates[0].non_material_metadata["selectionStrategy"],
                "ranking": ranking,
                "authorizedAuditionRank": 1,
                "voiceBinding": "PENDING",
                "identityRenameInvariant": True,
            }
        )
        propagation.append(
            {
                "spokenContentId": dialogue_id,
                "speakerKey": request.speaker_key,
                "characterUnderstandingId": request.voice_profile.character_understanding.understanding_id,
                "voiceProfileId": request.voice_profile.profile_id,
                "sceneStateSchema": request.scene_state.schema_version,
                "performanceModel": "baseline-plus-scene-delta",
                "selectedProvider": candidates[0].provider,
                "selectedModel": candidates[0].model,
                "selectedVoiceCandidate": candidates[0].voice_id,
                "voiceBinding": "PENDING",
                "exactTextHash": exact["sha256"],
                "audioInputFingerprint": audio_input_fingerprint(bound),
                "providerRequestFingerprint": _sha256_json(provider_payload),
                "providerInstructionSha256": hashlib.sha256(
                    instruction.encode("utf-8")
                ).hexdigest(),
                "providerInstruction": instruction,
                "semanticInvariantChecks": {
                    "restraintDoesNotForceLowEnergy": "不得把高克制解释为低能量"
                    in instruction,
                    "physicalBurdenDoesNotForceLowControl": "不得把身体负担解释为低控制力"
                    in instruction,
                    "ageDoesNotForceSlowPace": "不得把年龄解释为必然拖慢语速"
                    in instruction,
                    "authorityDoesNotForceLoudness": "不得把责任或权力解释为提高音量"
                    in instruction,
                },
            }
        )
        requests.append(request)

    if not all(
        all(item["semanticInvariantChecks"].values()) for item in propagation
    ):
        raise ValueError("semantic invariant propagation failed")

    output = args.output_directory
    output.mkdir(parents=True, exist_ok=True)
    _write(
        output / "character-understanding-7.2s-r.json",
        {
            "schemaVersion": "batch-7.2s-r-character-understanding-v1",
            "skillCode": source["skillCode"],
            "skillActuallyInvoked": True,
            "paidProviderCalls": 0,
            "orderedToolCalls": source["orderedToolCalls"],
            "neutralityAudit": source["neutralityAudit"],
            "items": [
                item.model_dump(mode="json", by_alias=True)
                for item in understandings
            ],
        },
    )
    _write(
        output / "voice-profile-7.2s-r.json",
        {
            "schemaVersion": "batch-7.2s-r-voice-profile-v1",
            "voiceBinding": "PENDING",
            "items": [
                item.model_dump(mode="json", by_alias=True) for item in profiles
            ],
        },
    )
    _write(
        output / "voice-candidate-ranking-7.2s-r.json",
        {
            "schemaVersion": "batch-7.2s-r-candidate-ranking-v1",
            "candidateLimit": 3,
            "items": candidate_evidence,
        },
    )
    _write(
        output / "performance-intent-7.2s-r.json",
        {
            "schemaVersion": "batch-7.2s-r-performance-intent-v1",
            "sceneStates": [
                item.model_dump(mode="json", by_alias=True) for item in states
            ],
            "performanceIntents": source["performanceIntents"],
        },
    )
    _write(
        output / "semantic-propagation-7.2s-r.json",
        {
            "schemaVersion": "batch-7.2s-r-semantic-propagation-v1",
            "paidProviderCalls": 0,
            "items": propagation,
        },
    )
    _write(
        output / "generation-request-7.2s-r.json",
        {
            "schemaVersion": "batch-7.2s-r-generation-request-v1",
            "skillCode": source["skillCode"],
            "voiceBinding": "PENDING",
            "requests": [
                item.model_dump(mode="json", by_alias=True) for item in requests
            ],
        },
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "skillActuallyInvoked": True,
                "paidProviderCalls": 0,
                "characterUnderstandings": len(understandings),
                "voiceProfiles": len(profiles),
                "candidateRankings": len(candidate_evidence),
                "identityRenameInvariant": True,
                "semanticInvariants": True,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
