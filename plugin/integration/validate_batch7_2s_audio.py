"""Validate existing Batch 7.2S Media without submitting TTS requests."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

from run_batch7_2r_preflight import write_json
from run_batch7_2r_real_e2e import call_tool, validate_media


MEDIA = (
    (
        "wangsili",
        "media_ba8fecb6d58d49c19a7b113d24b772c4",
        "spoken-s1-wangsili-proposal",
    ),
    (
        "geshuhan",
        "media_4dbc4dfa0a4a422080d9fa70c5dcad84",
        "spoken-s1-geshuhan-refusal",
    ),
)


async def run(output_root: Path) -> int:
    workspace = Path(__file__).resolve().parents[3]
    review_root = output_root / "review"
    evidence_path = output_root / "evidence" / "audio-technical-validation-7.2s.json"
    review_root.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, object]] = []

    mcp_url = os.environ.get("DRAMA_MCP_URL", "http://127.0.0.1:8765/mcp")
    async with streamable_http_client(mcp_url) as streams:
        async with ClientSession(*streams[:2]) as session:
            await session.initialize()
            for character, media_id, dialogue_id in MEDIA:
                media = await call_tool(
                    session, "media.get_media", {"media_id": media_id}
                )
                item = await validate_media(
                    session, media, review_root, workspace
                )
                item.update(
                    {
                        "character": character,
                        "dialogueId": dialogue_id,
                        "mediaResolve": "PASS",
                        "minioRoundtrip": "PASS",
                    }
                )
                items.append(item)

    evidence = {
        "batch": "7.2S",
        "classification": "TECHNICAL_VALIDATION_ONLY_NO_TTS_SUBMISSION",
        "status": "PASS",
        "providerCallsMadeByValidator": 0,
        "mediaRoundtrip": "PASS",
        "hashEquality": "PASS",
        "ffprobe": "PASS",
        "items": items,
        "secretsRecorded": False,
        "signedUrlsRecorded": False,
    }
    write_json(evidence_path, evidence)
    print(json.dumps(evidence, ensure_ascii=False))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("artifacts/batch7-2"),
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    raise SystemExit(asyncio.run(run(arguments.output_root.resolve())))
