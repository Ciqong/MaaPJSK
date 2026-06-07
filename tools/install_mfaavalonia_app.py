import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "install-mfaavalonia"
DEFAULT_CACHE = ROOT / ".cache"
MFA_REPO_API = "https://api.github.com/repos/MaaXYZ/MFAAvalonia/releases"
PYTHON_VERSION = "3.12.10"


def log(message: str) -> None:
    print(f"[mfa] {message}")


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
        file.write("\n")


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        log(f"Using cached {dest.name}")
        return dest

    log(f"Downloading {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "MaaPJSK"})
    with urllib.request.urlopen(request) as response, dest.open("wb") as file:
        shutil.copyfileobj(response, file)
    return dest


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def get_release(tag: str | None):
    url = f"{MFA_REPO_API}/latest" if not tag else f"{MFA_REPO_API}/tags/{tag}"
    request = urllib.request.Request(url, headers={"User-Agent": "MaaPJSK"})
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def select_mfa_asset(release, platform: str) -> dict:
    suffix = {
        "win-x64": "win-x64.zip",
        "win-arm64": "win-arm64.zip",
    }[platform]

    for asset in release["assets"]:
        if asset["name"].endswith(suffix):
            return asset
    names = ", ".join(asset["name"] for asset in release["assets"])
    raise RuntimeError(f"No MFAAvalonia asset for {platform}. Available: {names}")


def extract_zip(zip_path: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(dest)


def find_app_root(extract_dir: Path) -> Path:
    direct = extract_dir / "MFAAvalonia.exe"
    if direct.exists():
        return extract_dir

    matches = list(extract_dir.rglob("MFAAvalonia.exe"))
    if not matches:
        raise RuntimeError(f"MFAAvalonia.exe not found under {extract_dir}")
    return matches[0].parent


def copytree(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def clean_generated_files(path: Path) -> None:
    for cache_dir in path.rglob("__pycache__"):
        shutil.rmtree(cache_dir, ignore_errors=True)
    for pyc in path.rglob("*.pyc"):
        pyc.unlink(missing_ok=True)


def copy_project_files(output: Path, version: str) -> None:
    copytree(ROOT / "assets" / "resource", output / "resource")
    copytree(ROOT / "agent", output / "agent")
    copytree(ROOT / "config", output / "config")

    tools_dir = output / "tools"
    tools_dir.mkdir(exist_ok=True)
    shutil.copy2(ROOT / "tools" / "check_project.py", tools_dir / "check_project.py")

    for name in ("README.md", "DEVELOPMENT.md", "RUN_MFAAvalonia.md", "LICENSE", "requirements.txt"):
        src = ROOT / name
        if src.exists():
            shutil.copy2(src, output / name)

    interface = read_json(ROOT / "assets" / "interface.json")
    interface["version"] = version
    interface.setdefault("agent", {})
    interface["agent"]["child_exec"] = "./python/python.exe"
    interface["agent"]["child_args"] = ["-u", "./agent/main.py"]
    write_json(output / "interface.json", interface)


def setup_embedded_python(output: Path, cache: Path, version: str, arch: str) -> None:
    python_dir = output / "python"
    python_exe = python_dir / "python.exe"
    if python_exe.exists():
        log("Embedded Python already exists; refreshing dependencies")
    else:
        zip_name = f"python-{version}-embed-{arch}.zip"
        url = f"https://www.python.org/ftp/python/{version}/{zip_name}"
        zip_path = download(url, cache / zip_name)

        python_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(python_dir)

    pth_files = list(python_dir.glob("python*._pth"))
    if pth_files:
        pth = pth_files[0]
        lines = pth.read_text(encoding="utf-8").splitlines()
        normalized = []
        for line in lines:
            normalized.append("import site" if line.strip() == "#import site" else line)
        for required in (".", "Lib", "Lib\\site-packages"):
            if required not in normalized:
                normalized.append(required)
        pth.write_text("\n".join(normalized) + "\n", encoding="utf-8")

    get_pip = download("https://bootstrap.pypa.io/get-pip.py", cache / "get-pip.py")
    shutil.copy2(get_pip, python_dir / "get-pip.py")
    subprocess.run([str(python_exe), str(python_dir / "get-pip.py")], check=True)
    subprocess.run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run([str(python_exe), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")], check=True)


def write_launcher_files(output: Path) -> None:
    (output / "Start-MaaPJSK.bat").write_text(
        '@echo off\r\n'
        'cd /d "%~dp0"\r\n'
        'start "" "%~dp0MFAAvalonia.exe"\r\n',
        encoding="utf-8",
    )
    (output / "Check-Project.bat").write_text(
        '@echo off\r\n'
        'cd /d "%~dp0"\r\n'
        'python\\python.exe tools\\check_project.py\r\n'
        'python\\python.exe -c "import maa, numpy; print(\'OK: MaaFw and numpy import succeeded.\')"\r\n'
        'pause\r\n',
        encoding="utf-8",
    )


def verify_output(output: Path) -> None:
    required = [
        output / "MFAAvalonia.exe",
        output / "interface.json",
        output / "resource" / "pipeline" / "story.json",
        output / "agent" / "main.py",
        output / "python" / "python.exe",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError("Missing files:\n" + "\n".join(missing))

    subprocess.run([str(output / "python" / "python.exe"), str(output / "tools" / "check_project.py")], cwd=output, check=True)
    subprocess.run([str(output / "python" / "python.exe"), "-c", "import maa, numpy"], cwd=output, check=True)


def build(args) -> Path:
    cache = args.cache.resolve()
    output = args.output.resolve()
    temp_extract = cache / "mfa-extract"

    release = get_release(args.mfa_version)
    asset = select_mfa_asset(release, args.platform)
    zip_path = download(asset["browser_download_url"], cache / asset["name"])
    if asset.get("digest", "").startswith("sha256:"):
        expected = asset["digest"].split(":", 1)[1].lower()
        actual = sha256(zip_path).lower()
        if expected != actual:
            raise RuntimeError(f"SHA256 mismatch for {zip_path.name}: {actual} != {expected}")

    extract_zip(zip_path, temp_extract)
    app_root = find_app_root(temp_extract)

    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(app_root, output)

    copy_project_files(output, args.project_version)
    if not args.skip_python:
        setup_embedded_python(output, cache, args.python_version, args.python_arch)
    write_launcher_files(output)
    clean_generated_files(output)
    verify_output(output)
    clean_generated_files(output)

    if args.zip:
        archive = shutil.make_archive(str(output), "zip", output)
        log(f"Created {archive}")

    log(f"Install to {output}")
    return output


def parse_args():
    parser = argparse.ArgumentParser(description="Build an MFAAvalonia app package.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--mfa-version", default=None, help="Release tag, for example v2.12.1. Defaults to latest stable.")
    parser.add_argument("--platform", choices=["win-x64", "win-arm64"], default="win-x64")
    parser.add_argument("--project-version", default=read_json(ROOT / "assets" / "interface.json").get("version", "0.1.0"))
    parser.add_argument("--python-version", default=PYTHON_VERSION)
    parser.add_argument("--python-arch", choices=["amd64", "arm64"], default="amd64")
    parser.add_argument("--skip-python", action="store_true")
    parser.add_argument("--zip", action="store_true", help="Also create a zip archive next to the output directory.")
    return parser.parse_args()


if __name__ == "__main__":
    try:
        build(parse_args())
    except Exception as exc:
        log(f"ERROR: {exc}")
        sys.exit(1)
