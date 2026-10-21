"""Does the generated "Try it" snippet actually run?   python -m scripts.tryit_smoke [--per-task 4]

Takes small models (known size under 250 MB, safetensors weights) that the evaluation recommended, runs `guide.try_it_snippet`
for each in its own process and temporary directory, and records pass/fail. Snippets load weights only (no remote code).
Writes `eval/results/tryit_smoke.json`. Needs network access to the Hub's weight CDN.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import struct
import subprocess
import sys
import tempfile
import time
import wave
from collections import defaultdict
from pathlib import Path

from src import ingest
from src.guide import try_it_snippet

TASKS = ("automatic-speech-recognition", "translation", "text-classification", "token-classification", "sentence-similarity")


def write_wav(path: Path, seconds: float = 1.0, rate: int = 16000) -> None:
    with wave.open(str(path), "w") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(3000 * math.sin(2 * math.pi * 220 * i / rate))) for i in range(int(seconds * rate))))


def has_safetensors(model_id: str) -> bool:
    try:
        meta, _ = ingest.load_raw(model_id)
    except Exception:
        return False
    return any(s.get("rfilename") == "model.safetensors" for s in meta.get("siblings", []))


def pick(per_task: int) -> list[dict]:
    recs = {}
    for line in gzip.open(sorted(Path("data").glob("snapshot-*/records.jsonl.gz"))[-1], "rt", encoding="utf-8"):
        r = json.loads(line)
        recs[r["model_id"]] = r
    seen = json.load(open("eval/results/raw-v2.json", encoding="utf-8"))["outcomes"]["ours"]
    by_task: dict[str, list[dict]] = defaultdict(list)
    for q in seen.values():
        for m in q["top"]:
            r = recs.get(m["model_id"])
            if r and r["task"] in TASKS and r["size_status"] == "known" and r["size_mb"] <= 250 and has_safetensors(r["model_id"]):
                if r not in by_task[r["task"]]:
                    by_task[r["task"]].append(r)
    return [r for t in TASKS for r in sorted(by_task[t], key=lambda r: r["size_mb"])[:per_task]]


def run(rec: dict, workdir: Path, timeout: int) -> dict:
    code = try_it_snippet(rec["model_id"], rec["task"])
    d = Path(tempfile.mkdtemp(dir=workdir))
    write_wav(d / "audio.wav")
    t = time.time()
    try:
        p = subprocess.run([sys.executable, "-I", "-c", code], cwd=d, capture_output=True, text=True, timeout=timeout,
                           env={**__import__("os").environ, "HF_HOME": str(workdir / "hf")})
        ok, tail = p.returncode == 0, (p.stdout if p.returncode == 0 else p.stderr)[-400:]
    except subprocess.TimeoutExpired:
        ok, tail = False, f"timeout after {timeout}s"
    return {"model_id": rec["model_id"], "task": rec["task"], "size_mb": round(rec["size_mb"], 1), "ok": ok,
            "seconds": round(time.time() - t, 1), "tail": tail.strip()[-300:]}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-task", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=240)
    ap.add_argument("--workdir", default="/tmp/tryit")
    args = ap.parse_args(argv)
    work = Path(args.workdir)
    work.mkdir(parents=True, exist_ok=True)
    results = []
    for rec in pick(args.per_task):
        r = run(rec, work, args.timeout)
        print(("OK  " if r["ok"] else "FAIL"), r["task"], r["model_id"], r["seconds"], "s", "" if r["ok"] else r["tail"][-160:].replace("\n", " "))
        results.append(r)
    out = {"models": len(results), "passed": sum(r["ok"] for r in results), "results": results}
    Path("eval/results/tryit_smoke.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{out['passed']}/{out['models']} snippets ran")


if __name__ == "__main__":
    main()
