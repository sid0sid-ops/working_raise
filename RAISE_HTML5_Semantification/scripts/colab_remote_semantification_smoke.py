from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

REMOTE_ARCHIVE = Path("/content/raise_html5_semantification.tar.gz")
REMOTE_PROJECT = Path("/content/RAISE_HTML5_Semantification")


def run(command: list[str], cwd: Path | None = None) -> None:
    print(f"$ {' '.join(command)}")
    completed = subprocess.run(command, cwd=cwd, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {completed.returncode}: {command}")


def find_project_root() -> Path:
    local_root = Path.cwd()
    if (local_root / "pyproject.toml").exists():
        return local_root

    if REMOTE_ARCHIVE.exists():
        if REMOTE_PROJECT.exists():
            print(f"Removing existing extracted project: {REMOTE_PROJECT}")
            shutil.rmtree(REMOTE_PROJECT)
        print(f"Extracting {REMOTE_ARCHIVE} to /content")
        with tarfile.open(REMOTE_ARCHIVE, "r:gz") as archive:
            archive.extractall("/content")
        if (REMOTE_PROJECT / "pyproject.toml").exists():
            return REMOTE_PROJECT

    raise FileNotFoundError(
        "Could not find project root. Upload raise_html5_semantification.tar.gz "
        "to /content before running this script on Colab."
    )


def runtime_info() -> dict[str, str]:
    return {
        "platform": platform.platform(),
        "colab_tpu_addr": os.environ.get("COLAB_TPU_ADDR", ""),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES", ""),
    }


def ensure_project_installed(project_root: Path) -> None:
    if importlib.util.find_spec("raise_html5_semantification"):
        print("Package is already importable; skipping editable install.")
        return
    run([sys.executable, "-m", "pip", "install", "-q", "-e", ".[dev]"], cwd=project_root)


def main() -> None:
    info = runtime_info()
    print("Colab runtime info:")
    print(json.dumps(info, indent=2))
    if info["colab_tpu_addr"]:
        print("TPU runtime detected. Semantification will still run as deterministic CPU work.")
    else:
        print("No TPU detected in environment variables.")

    project_root = find_project_root()
    print(f"Project root: {project_root}")

    ensure_project_installed(project_root)
    fixtures = sorted((project_root / "tests/fixtures").glob("*.json"))
    if not fixtures:
        raise FileNotFoundError("No JSON fixtures found for Colab smoke testing.")

    for pass_index in range(1, 3):
        print(f"Colab semantification pass {pass_index}")
        for fixture in fixtures:
            output_stem = f"colab_pass{pass_index}_{fixture.stem}"
            run(
                [
                    sys.executable,
                    "-m",
                    "raise_html5_semantification",
                    "validate",
                    "--input",
                    str(fixture),
                ],
                cwd=project_root,
            )
            run(
                [
                    sys.executable,
                    "-m",
                    "raise_html5_semantification",
                    "build",
                    "--input",
                    str(fixture),
                    "--output",
                    f"data/output/{output_stem}.html",
                    "--validation-output",
                    f"data/output/{output_stem}_validation.json",
                    "--profile-output",
                    f"data/output/{output_stem}_profile.json",
                ],
                cwd=project_root,
            )
    run([sys.executable, "-m", "pytest"], cwd=project_root)

    generated = sorted((project_root / "data/output").glob("colab_pass*"))
    if not generated:
        raise FileNotFoundError("No Colab smoke outputs were generated.")
    for output_path in generated:
        print(f"Generated {output_path} ({output_path.stat().st_size} bytes)")

    print("Colab semantification smoke test completed successfully.")


if __name__ == "__main__":
    main()
