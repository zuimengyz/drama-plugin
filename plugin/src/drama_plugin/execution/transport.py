"""Provider transport port and a recorded, local-only proof transport.

No legacy orchestration or generation provider is reachable from this module.
The request serializer transfers the approved prompt without enhancement.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from drama_plugin.contracts.base import canonical_json
from drama_plugin.execution.contracts import ExecutionOperation, ProviderAttempt, ProviderReceipt, ProviderRequest, ProviderResult


class DefinitelyNotSubmitted(RuntimeError):
    """Transport has positive evidence that no request was sent."""

    def __init__(self, code: str = "DEFINITELY_NOT_SUBMITTED", *, http_status: int | None = None):
        super().__init__(code)
        self.code, self.http_status = code, http_status


class PossiblySubmitted(RuntimeError):
    """Transport cannot confirm reception; never a generation retry signal."""

    def __init__(self, code: str = "SUBMISSION_UNCERTAIN", *, http_status: int | None = None):
        super().__init__(code)
        self.code, self.http_status = code, http_status


class CapabilityAbsent(RuntimeError):
    pass


class RecoveryIdentityUnavailable(RuntimeError):
    """No supported exact remote identity; absence of a task is not established."""


def failure_details(error: BaseException, *, stage: str = "EXECUTION_SUBMIT"):
    import re
    from drama_plugin.generation.contracts import ExecutionFailureDetails
    from drama_plugin.providers.video.diagnostics import identifier
    types, codes, frames, seen = [], [], [], set()
    status = None
    current = error
    while current is not None and id(current) not in seen and len(types) < 8:
        seen.add(id(current))
        types.append(type(current).__name__)
        code = getattr(current, 'code', None) or getattr(current, 'error_code', None)
        if isinstance(code, str) and re.fullmatch(r'[A-Z][A-Z0-9_:.]{0,199}', code):
            codes.append(code)
        status = status or getattr(current, 'http_status', None) or getattr(current, 'status_code', None)
        trace = current.__traceback__
        while trace is not None:
            code = trace.tb_frame.f_code
            # No absolute path, source line, frame locals or exception text.
            frame = f"{Path(code.co_filename).name}:{code.co_name}:{trace.tb_lineno}"
            frames.append(re.sub(r"\s", "_", frame)[-256:])
            trace = trace.tb_next
        current = current.__cause__ or (None if current.__suppress_context__ else current.__context__)
    details = getattr(error, "provider_diagnostics", {})
    return ExecutionFailureDetails(stage=getattr(error, "submission_stage", stage),
        request_started=getattr(error, "request_started", None),
        exception_types=tuple(types), error_codes=tuple(codes), traceback_frames=tuple(frames[-32:]),
        http_status=details.get("http_status") or status,
        request_id=identifier(details.get("request_id"), ""),
        official_error_code=identifier(details.get("official_error_code"), ""))


class IntakeTransient(RuntimeError):
    pass


def serialize_request(request: ProviderRequest) -> bytes:
    payload = request.model_dump(mode="json", by_alias=True)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    if json.loads(encoded)["promptText"] != request.prompt_text:
        raise ValueError("FinalPrompt exact transfer failed")
    return encoded


class ProviderTransport(Protocol):
    @property
    def provider(self) -> str: ...
    @property
    def offline(self) -> bool: ...
    def can_reconcile(self, attempt: ProviderAttempt, receipt: ProviderReceipt | None) -> bool: ...
    async def submit(self, operation: ExecutionOperation, attempt: ProviderAttempt,
                     request: ProviderRequest) -> ProviderReceipt: ...
    async def query(self, operation: ExecutionOperation, attempt: ProviderAttempt,
                    receipt: ProviderReceipt | None) -> ProviderReceipt | None: ...
    async def obtain(self, result: ProviderResult) -> bytes: ...


class ReplayTransport:
    """Synthetic remote state retained outside Python memory for crash proofs.

    The append-only submission log counts actual invocations, independently of
    receipt deduplication. The remote file is written before synthetic ACK loss.
    """
    provider = "offline-replay"
    offline = True

    def __init__(self, directory: Path, result: ProviderResult, *,
                 behavior: str = "success", query_available: bool = True):
        if not directory.is_absolute():
            raise ValueError("Replay directory must be absolute")
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.result = ProviderResult.model_validate(result.model_dump())
        if behavior not in {"success", "ack-loss", "running", "failed", "not-submitted", "crash-after-send"}:
            raise ValueError("Unknown replay behavior")
        self.behavior = behavior
        self.query_available = query_available

    def _path(self, attempt: ProviderAttempt) -> Path:
        return self.directory / (attempt.client_identity + ".json")

    def can_reconcile(self, attempt: ProviderAttempt, receipt: ProviderReceipt | None) -> bool:
        return self.query_available and (receipt is not None or self._path(attempt).exists())

    async def submit(self, operation: ExecutionOperation, attempt: ProviderAttempt,
                     request: ProviderRequest) -> ProviderReceipt:
        if self.behavior == "not-submitted":
            raise DefinitelyNotSubmitted()
        with (self.directory / "submissions.jsonl").open("ab", buffering=0) as log:
            log.write(serialize_request(request) + b"\n")
            import os
            os.fsync(log.fileno())
        state = "RUNNING" if self.behavior == "running" else "FAILED" if self.behavior == "failed" else "SUCCEEDED"
        receipt = ProviderReceipt.seal(scope=operation.scope, run_id=operation.run_id,
            source_package_ref=operation.source_package_ref, operation_ref=operation.artifact_reference(),
            attempt_ref=attempt.artifact_reference(), provider=self.provider,
            client_identity=attempt.client_identity, request_fingerprint=attempt.request_fingerprint,
            remote_identity="replay:" + attempt.client_identity, state=state,
            result=self.result if state == "SUCCEEDED" else None,
            failure_code="PROVIDER_REJECTED" if state == "FAILED" else None)
        from drama_plugin.execution.media import atomic_write
        atomic_write(self._path(attempt), canonical_json(receipt).encode())
        if self.behavior == "ack-loss":
            raise PossiblySubmitted()
        if self.behavior == "crash-after-send":
            import os
            os._exit(73)  # Only opt-in offline subprocess recovery fixtures.
        return receipt

    async def query(self, operation: ExecutionOperation, attempt: ProviderAttempt,
                    receipt: ProviderReceipt | None) -> ProviderReceipt | None:
        if not self.query_available or not self._path(attempt).exists():
            return None
        return ProviderReceipt.model_validate_json(self._path(attempt).read_bytes())

    async def obtain(self, result: ProviderResult) -> bytes:
        # No network, HTTP URL or credential even if present in the environment.
        path = Path(result.locator)
        if not path.is_absolute() or "://" in result.locator:
            raise ValueError("Replay result must be a local absolute fixture")
        try:
            return path.read_bytes()
        except OSError as error:
            raise IntakeTransient() from error
