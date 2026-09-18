"""Isolated MLX bridge. Run by absolute file using the already installed model Python.

Stdlib-only bootstrap; no dependency installation, cloud client, keys or formal store.
This audits Python network/process attempts; native-library traffic is not packet-captured.
"""
from __future__ import annotations

import importlib
import json
import resource
import sys
import time
from pathlib import Path
from typing import Any


def main() -> None:
    job = json.loads(Path(sys.argv[1]).read_text())
    root = Path(job['root']).resolve()
    metrics: dict[str, Any] = {'networkAttempts':0, 'downloads':0, 'modelLoadSeconds':{},
                               'tokenCounts':[], 'providerMonetaryCost':0,
                               'totalCost':'NOT_ZERO_LOCAL_COMPUTE', 'pythonVersion':sys.version}

    def audit(event: str, args: tuple[Any, ...]) -> None:
        if event.startswith('socket.') or event in {'subprocess.Popen', 'os.system', 'os.posix_spawn'}:
            metrics['networkAttempts'] += 1
            raise RuntimeError('OFFLINE_EXECUTION_NO_NETWORK_OR_CHILD_PROCESS')
        if event == 'open' and args and isinstance(args[0], str):
            p = Path(args[0])
            if p.name in {'token', 'stored_tokens'}:
                raise RuntimeError('CREDENTIAL_READ_FORBIDDEN')

    sys.addaudithook(audit)
    sys.path[:0] = [str(root / 'scripts'), str(root)]
    weights: Any = importlib.import_module('weights')

    def local_only(rel: str, verbose: bool = True) -> Path:
        p = root / rel
        if not p.is_file() or p.stat().st_size == 0:
            raise RuntimeError('LOCAL_MODEL_INCOMPLETE_NO_DOWNLOAD: ' + rel)
        return p

    weights.ensure_local = local_only
    weights.is_present = lambda rel: (root / rel).is_file()
    sa: Any = importlib.import_module('sa3_mlx')
    if job['model'] not in {'medium', 'sm-music'}:
        raise ValueError('UNSUPPORTED_MODEL')
    codec = 'same-l' if job['model'] == 'medium' else 'same-s'
    needed = [sa.T5GEMMA_NPZ_REL, sa.DIT_CHOICES[job['model']]['ckpt'], sa.DECODER_CHOICES[codec][3]]
    if job['initAudio']:
        needed.append(sa.ENCODER_CHOICES[codec][2])
    for rel in needed:
        local_only(rel)
    # The original function has download semantics; don't call it at all.
    sa._preflight_download = lambda args: [local_only(rel) for rel in needed]
    orig_encode = sa.T5Gemma.encode

    def checked_encode(self: Any, prompts: list[str], max_len: int = 256) -> Any:
        counts = [len(self.tokenizer.Encode(p)) for p in prompts]
        metrics['tokenCounts'].extend(counts)
        if any(n > max_len for n in counts):
            raise ValueError('PROMPT_TRUNCATION_FORBIDDEN')
        return orig_encode(self, prompts, max_len=max_len)

    sa.T5Gemma.encode = checked_encode
    # Measure loader wall time, leaving native implementation and model untouched.
    for name in ('load_dit', 'load_decoder', 'load_conditioner_from_npz'):
        original = getattr(sa, name)
        def timed(*args: Any, _fn: Any = original, _name: str = name, **kwargs: Any) -> Any:
            t = time.monotonic()
            value = _fn(*args, **kwargs)
            metrics['modelLoadSeconds'][_name] = time.monotonic() - t
            return value
        setattr(sa, name, timed)
    original_t5 = sa.T5Gemma.from_npz

    def timed_t5(path: str) -> Any:
        t = time.monotonic()
        value = original_t5(path)
        metrics['modelLoadSeconds']['T5Gemma'] = time.monotonic() - t
        return value

    sa.T5Gemma.from_npz = timed_t5
    sys.argv = ['sa3_mlx.py', '--dit', job['model'], '--decoder', codec,
                '--prompt', job['prompt'], '--negative-prompt', job['negative'],
                '--seconds', str(job['duration']), '--steps', '8', '--cfg', '3.0',
                '--seed', str(job['seed']), '--out', job['output']]
    if job['initAudio']:
        sys.argv += ['--init-audio', job['initAudio'], '--init-noise-level', str(job['noise'])]
    if job['editWindow']:
        sys.argv += ['--inpaint-range', ','.join(str(x) for x in job['editWindow'])]
    t = time.monotonic()
    try:
        sa.main()
        metrics.update(modelLoaded=True, device='Metal', model=job['model'],
                       mlxPeakBytes=sa._CUMULATIVE_PEAK_B, stagePeakBytes=sa._STAGE_PEAKS)
    finally:
        metrics.update(wallSeconds=time.monotonic()-t, peakRSSBytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                       networkObservation='Python audit deny socket/process; offline resolver; no native packet capture',
                       providerDurationMethod='Native CLI latent ceil then trims sub-latent excess; no adapter trimming')
        Path(job['metrics']).write_text(json.dumps(metrics, indent=2)+'\n')


if __name__ == '__main__':
    main()
