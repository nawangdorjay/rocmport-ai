from __future__ import annotations

import shutil
import tempfile
import urllib.parse
import urllib.request
import os
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path


IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    ".cache",
}

TEXT_EXTENSIONS = {
    "",
    ".cfg",
    ".conf",
    ".dockerfile",
    ".env",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

MAX_FILE_BYTES = 512_000
MAX_ZIP_FILES = 700
MAX_ZIP_BYTES = 60 * 1024 * 1024


@dataclass(frozen=True)
class PreparedRepo:
    path: Path
    name: str
    temp_dir: Path | None = None


def sample_repo_path(project_root: Path) -> Path:
    return project_root / "samples" / "cuda_first_repo"


def prepare_uploaded_zip(zip_path: str | Path) -> PreparedRepo:
    temp_dir = make_work_dir("rocmport-upload-")
    extract_zip(Path(zip_path), temp_dir)
    repo_path = _single_child_or_self(temp_dir)
    return PreparedRepo(path=repo_path, name=repo_path.name, temp_dir=temp_dir)


def prepare_github_repo(github_url: str, branch: str = "main") -> PreparedRepo:
    owner, repo = parse_github_url(github_url)
    temp_dir = make_work_dir("rocmport-github-")
    zip_path = temp_dir / f"{repo}-{branch}.zip"
    url = f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{branch}"
    urllib.request.urlretrieve(url, zip_path)
    extract_zip(zip_path, temp_dir / "src")
    repo_path = _single_child_or_self(temp_dir / "src")
    return PreparedRepo(path=repo_path, name=repo, temp_dir=temp_dir)


def parse_github_url(github_url: str) -> tuple[str, str]:
    parsed = urllib.parse.urlparse(github_url.strip())
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        raise ValueError("Use a public GitHub repository URL from github.com.")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise ValueError("GitHub URL must include owner and repository name.")
    owner, repo = parts[0], parts[1].removesuffix(".git")
    if not owner or not repo:
        raise ValueError("GitHub URL must include owner and repository name.")
    return owner, repo


def extract_zip(zip_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    total_size = 0
    with zipfile.ZipFile(zip_path) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_ZIP_FILES:
            raise ValueError(f"ZIP has too many files ({len(infos)} > {MAX_ZIP_FILES}).")
        for info in infos:
            total_size += info.file_size
            if total_size > MAX_ZIP_BYTES:
                raise ValueError("ZIP is too large for the demo scanner.")
            target = destination / info.filename
            resolved = target.resolve()
            if not _is_within(resolved, destination.resolve()):
                raise ValueError("ZIP contains an unsafe path.")
            if info.is_dir():
                resolved.mkdir(parents=True, exist_ok=True)
                continue
            resolved.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as src, resolved.open("wb") as dst:
                shutil.copyfileobj(src, dst)


def iter_text_files(root: Path) -> list[tuple[str, str]]:
    files: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in path.relative_to(root).parts):
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            continue
        if not _is_probable_text_file(path):
            continue
        relative_path = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                text = path.read_text(encoding="latin-1")
            except UnicodeDecodeError:
                continue
        files.append((relative_path, text))
    return files


def make_work_dir(prefix: str) -> Path:
    configured = os.getenv("ROCMPORT_TMP_DIR", "").strip()
    base = Path(configured) if configured else Path(tempfile.gettempdir())
    base.mkdir(parents=True, exist_ok=True)
    for _ in range(100):
        candidate = base / f"{prefix}{uuid.uuid4().hex}"
        try:
            candidate.mkdir(parents=True, exist_ok=False)
            return candidate
        except FileExistsError:
            continue
    raise RuntimeError("Could not create a ROCmPort work directory.")


def _is_probable_text_file(path: Path) -> bool:
    if path.name in {"Dockerfile", "Makefile", "requirements.txt"}:
        return True
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    return path.name.lower().startswith("dockerfile")


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False


def _single_child_or_self(path: Path) -> Path:
    children = [child for child in path.iterdir() if child.name != "__MACOSX"]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return path
