from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes
import json
import os
import statistics
import time
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort
from PIL import Image
from rembg import new_session, remove
from rembg.sessions import sessions_class


class _ProcessMemoryCountersEx(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.wintypes.DWORD),
        ("PageFaultCount", ctypes.wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]


def _private_memory_mb() -> tuple[float, float]:
    if os.name != "nt":
        import tracemalloc

        current, peak = tracemalloc.get_traced_memory()
        return current / 1024**2, peak / 1024**2
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.restype = ctypes.wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = (
        ctypes.wintypes.HANDLE,
        ctypes.POINTER(_ProcessMemoryCountersEx),
        ctypes.wintypes.DWORD,
    )
    psapi.GetProcessMemoryInfo.restype = ctypes.wintypes.BOOL
    counters = _ProcessMemoryCountersEx()
    counters.cb = ctypes.sizeof(counters)
    if not psapi.GetProcessMemoryInfo(
        kernel32.GetCurrentProcess(),
        ctypes.byref(counters),
        counters.cb,
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    return counters.PrivateUsage / 1024**2, counters.PeakPagefileUsage / 1024**2


def _synthetic_tissue(size: int = 1024) -> np.ndarray:
    y, x = np.mgrid[0:size, 0:size]
    image = np.full((size, size, 3), (88, 92, 96), dtype=np.uint8)
    subject = ((x - size * 0.48) / (size * 0.30)) ** 2 + (
        (y - size * 0.50) / (size * 0.34)
    ) ** 2 < 1
    texture = np.sin(x / 19.0) * 18.0 + np.cos(y / 23.0) * 14.0 + np.sin((x + y) / 31.0) * 9.0
    image[subject] = np.clip(
        np.stack(
            (
                92 + texture[subject] * 0.45,
                132 + texture[subject],
                82 + texture[subject] * 0.35,
            ),
            axis=1,
        ),
        0,
        255,
    ).astype(np.uint8)
    return image


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return ordered[index]


def _load_sample(path: Path | None) -> np.ndarray:
    if path is None:
        return _synthetic_tissue()
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure rembg BiRefNet on one image")
    parser.add_argument("--image", type=Path, help="RGB/RGBA sample; default is synthetic")
    parser.add_argument("--model", default="birefnet-general")
    parser.add_argument("--providers", default="CPUExecutionProvider")
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--mask-output", type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    if args.runs < 1 or args.warmup < 0:
        parser.error("runs must be positive and warmup must be non-negative")

    providers = [item.strip() for item in args.providers.split(",") if item.strip()]
    image = _load_sample(args.image)
    session_class = next(
        (item for item in sessions_class if item.name() == args.model),
        None,
    )
    if session_class is None:
        parser.error(f"unknown rembg model: {args.model}")
    model_path = Path(session_class.model_dir()) / f"{args.model}.onnx"
    model_was_cached = model_path.exists()
    before_current, before_peak = _private_memory_mb()
    started = time.perf_counter()
    session = new_session(args.model, providers=providers)
    session_load_seconds = time.perf_counter() - started
    model_path = Path(session.__class__.download_models())
    outputs = [remove(image, session=session, only_mask=True) for _ in range(args.warmup)]
    durations: list[float] = []
    for _ in range(args.runs):
        started = time.perf_counter()
        outputs = [remove(image, session=session, only_mask=True)]
        durations.append(time.perf_counter() - started)
    after_current, after_peak = _private_memory_mb()
    mask = np.asarray(outputs[0], dtype=np.uint8)
    selected_providers = session.inner_session.get_providers()
    if args.mask_output is not None:
        args.mask_output.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(mask, mode="L").save(args.mask_output)

    result: dict[str, Any] = {
        "model": args.model,
        "sample": str(args.image) if args.image is not None else "synthetic",
        "sample_shape": list(image.shape),
        "model_path": str(model_path),
        "model_size_bytes": model_path.stat().st_size,
        "model_was_cached_before_load": model_was_cached,
        "session_load_seconds": session_load_seconds,
        "session_load_includes_download": not model_was_cached,
        "inference_runs": args.runs,
        "inference_warmup_runs": args.warmup,
        "inference_p50_seconds": _percentile(durations, 0.50),
        "inference_p95_seconds": _percentile(durations, 0.95),
        "inference_mean_seconds": statistics.fmean(durations),
        "private_mb_before_load": before_current,
        "private_mb_after_runs": after_current,
        "private_peak_mb_process": max(before_peak, after_peak),
        "onnxruntime_providers_available": ort.get_available_providers(),
        "onnxruntime_providers_selected": selected_providers,
        "directml_available": "DirectMLExecutionProvider" in ort.get_available_providers(),
        "mask_shape": list(mask.shape),
        "mask_min": int(mask.min()),
        "mask_max": int(mask.max()),
        "mask_nonzero_fraction": float(np.count_nonzero(mask) / mask.size),
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    print(payload)
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
