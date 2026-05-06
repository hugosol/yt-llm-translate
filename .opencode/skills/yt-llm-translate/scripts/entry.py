"""yt-llm-translate entry point.

Usage:
    python entry.py <youtube_url>

Pipeline: download.ps1 -> srt-punctuator -> resegment.py -> batch_translate.py

All output files (MP4, SRT) go to the user's current working directory.
"""

import sys
import json
import time
import subprocess
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPTS_DIR / "config.json"
RUN_OPENCODE = SCRIPTS_DIR / "run_opencode.py"


def load_config():
    if not CONFIG_PATH.exists():
        return {}
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"[WARN] Failed to parse config.json: {e}", file=sys.stderr)
        return {}


def needs_punctuation(srt_path: Path) -> bool:
    config = load_config()
    punct_cfg = config.get("punctuation_check", {})
    expected_per_lines = punct_cfg.get("expected_per_lines", 1.0 / 3)
    threshold_factor = punct_cfg.get("threshold_factor", 0.4)

    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    blocks = content.strip().split('\n\n')
    text_lines = []

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        for line in lines[2:]:
            stripped = line.strip()
            if stripped:
                text_lines.append(stripped)

    if not text_lines:
        return False

    punct_count = sum(line.count(c) for line in text_lines for c in ('.', '?', '!'))
    expected = len(text_lines) * expected_per_lines
    threshold = expected * threshold_factor

    return punct_count < threshold


def invoke_srt_punctuator(srt_path: Path, cwd: Path) -> bool:
    prompt = f"使用skill: srt-punctuator, 为这个SRT字幕文件添加英文标点符号 {srt_path}"
    log_file = cwd / "srt_punctuator.log"

    cmd = [
        sys.executable, str(RUN_OPENCODE),
        "--prompt", prompt,
        "--expected-file", str(srt_path),
        "--workdir", str(cwd),
        "--log-file", str(log_file),
        "--timeout", "600",
    ]

    print(f"[OPENCODE] Invoking srt-punctuator for {srt_path.name}")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd),
    )

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode == 0:
        print("[OK] srt-punctuator completed successfully")
        return True
    else:
        print(f"[FAIL] opencode exited with code {result.returncode}")
        return False


def invoke_batch_translate(srt_path: Path, cwd: Path) -> bool:
    batch_script = SCRIPTS_DIR / "batch_translate.py"
    cmd = [
        sys.executable, str(batch_script), str(srt_path),
    ]

    print(f"[RUN] batch_translate.py on {srt_path.name}")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd),
    )

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode == 0:
        print("[OK] batch translate completed successfully")
        return True
    else:
        print(f"[FAIL] batch_translate.py exited with code {result.returncode}")
        return False


def invoke_resegment(srt_path: Path, cwd: Path) -> bool:
    resegment_script = SCRIPTS_DIR / "resegment.py"
    cmd = [sys.executable, str(resegment_script), str(srt_path)]

    print(f"[RUN] resegment.py on {srt_path.name}")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd),
    )

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode == 0:
        print("[OK] resegment completed successfully")
        return True
    else:
        print(f"[FAIL] resegment.py exited with code {result.returncode}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python entry.py <youtube_url>")
        sys.exit(1)

    url = sys.argv[1]
    if 'youtube.com/watch?v=' in url and '&' in url:
        url = url.split('&')[0]
    user_cwd = Path.cwd()
    sys.stdout.reconfigure(errors='replace')
    sys.stderr.reconfigure(errors='replace')

    config = load_config()
    before_srt = set(user_cwd.glob("*.srt"))

    # 1. download
    download_script = SCRIPTS_DIR / "download.ps1"
    if not download_script.exists():
        print(f"[FAIL] download.ps1 not found in {SCRIPTS_DIR}")
        sys.exit(1)

    print(f"[RUN] download.ps1 {url}")
    t0 = time.time()
    result = subprocess.run(
        ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", str(download_script), url],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(user_cwd),
    )
    t1 = time.time()
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        print(f"[FAIL] download.ps1 exited with code {result.returncode}")
        sys.exit(result.returncode)
    print(f"[TIME] download: {t1 - t0:.1f}s")

    # find English SRT
    new_srt = sorted(set(user_cwd.glob("*.srt")) - before_srt)
    eng_srt = [p for p in new_srt if p.match("*.en.srt")]
    if not eng_srt:
        print("[INFO] No English SRT (*.en.srt) found after download")
        print("[DONE] All steps completed.")
        return

    srt_path = eng_srt[0]

    # 2. punctuate
    t2 = time.time()
    if needs_punctuation(srt_path):
        if not invoke_srt_punctuator(srt_path, user_cwd):
            print("[ERROR] srt-punctuator failed, aborting")
            sys.exit(1)
        t3 = time.time()
        print(f"[TIME] punctuate: {t3 - t2:.1f}s")
    else:
        t3 = t2
        print("[INFO] English SRT already has sufficient punctuation, skipping srt-punctuator")

    # 3. resegment
    t4 = time.time()
    if not invoke_resegment(srt_path, user_cwd):
        print("[ERROR] resegment failed")
    t5 = time.time()
    print(f"[TIME] resegment: {t5 - t4:.1f}s")

    # 4. translate
    t6 = time.time()
    if not invoke_batch_translate(srt_path, user_cwd):
        print("[ERROR] batch translate failed")
    t7 = time.time()
    print(f"[TIME] translate: {t7 - t6:.1f}s")

    # 5. finalize: rename subtitles and cleanup temp files
    finalize_script = SCRIPTS_DIR / "finalize-subtitles.ps1"
    workspace_dir = user_cwd / f"{srt_path.stem}_workspace"
    t9 = t7
    if not finalize_script.exists():
        print(f"[FAIL] finalize-subtitles.ps1 not found in {SCRIPTS_DIR}")
    else:
        t8 = time.time()
        print(f"[RUN] finalize-subtitles.ps1 {srt_path.name}")
        finalize_result = subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", str(finalize_script),
             "-InputFile", str(srt_path),
             "-WorkspaceDir", str(workspace_dir)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(user_cwd),
        )
        if finalize_result.stdout:
            print(finalize_result.stdout)
        if finalize_result.stderr:
            print(finalize_result.stderr, file=sys.stderr)
        t9 = time.time()
        if finalize_result.returncode != 0:
            print(f"[WARN] finalize-subtitles.ps1 exited with code {finalize_result.returncode} (non-fatal)")
        else:
            print("[OK] finalize completed successfully")
        print(f"[TIME] finalize: {t9 - t8:.1f}s")

    print(f"[TIME] total: {t9 - t0:.1f}s")
    print("[DONE] All steps completed.")


if __name__ == "__main__":
    main()
