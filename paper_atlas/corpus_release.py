"""Build and verify a portable, versioned snapshot for the local MCP server."""

import argparse
import gzip
import hashlib
from io import BytesIO
import json
from pathlib import Path
import tarfile

from paper_atlas.query_core import PaperCorpus


REQUIRED = (
    Path("knn/cluster_umap10d_mcs15_ms5.npz"),
    Path("knn/cluster_labels.json"),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _add_bytes(archive: tarfile.TarFile, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = 0o644
    info.mtime = 0
    archive.addfile(info, BytesIO(data))


def build(data_dir: Path, output_dir: Path, version: str) -> Path:
    """Package only the files used by PaperCorpus, with stable ordering and metadata."""
    if not version or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-." for char in version):
        raise ValueError("version must contain only lowercase letters, digits, hyphens, and dots")
    data_dir = data_dir.resolve()
    parquet = sorted((data_dir / "normalized").glob("*/*.parquet"))
    if not parquet:
        raise FileNotFoundError("no normalized Parquet files found")
    paths = parquet + [data_dir / name for name in REQUIRED]
    for path in paths:
        if not path.is_file() or not path.resolve().is_relative_to(data_dir):
            raise FileNotFoundError(f"missing or unsafe corpus file: {path}")
    corpus = PaperCorpus(data_dir)  # checks IDs against the cluster snapshot
    files = [
        {"path": path.relative_to(data_dir).as_posix(), "bytes": path.stat().st_size,
         "sha256": _sha256(path)}
        for path in paths
    ]
    manifest = {
        "format_version": 1,
        "corpus_version": version,
        "paper_count": len(corpus.papers),
        "evidence_scope": "source metadata and abstract; no full-text verification",
        "files": files,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / f"paper-atlas-corpus-{version}.tar.gz"
    prefix = f"paper-atlas-corpus-{version}"
    with archive_path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w") as archive:
                _add_bytes(archive, f"{prefix}/manifest.json",
                           (json.dumps(manifest, indent=2) + "\n").encode())
                for path in paths:
                    _add_bytes(archive, f"{prefix}/{path.relative_to(data_dir).as_posix()}",
                               path.read_bytes())
    (output_dir / f"{archive_path.name}.sha256").write_text(
        f"{_sha256(archive_path)}  {archive_path.name}\n")
    return archive_path


def verify(archive_path: Path) -> dict:
    """Verify the published archive hash and every member against its manifest."""
    checksum_path = archive_path.with_name(f"{archive_path.name}.sha256")
    expected_hash, expected_name = checksum_path.read_text().strip().split("  ", 1)
    if expected_name != archive_path.name or _sha256(archive_path) != expected_hash:
        raise ValueError("archive SHA-256 mismatch")
    prefix = archive_path.name.removesuffix(".tar.gz")
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        if len(names) != len(set(names)) or any(not member.isfile() for member in members):
            raise ValueError("archive contains duplicate or non-file members")
        manifest_member = archive.extractfile(f"{prefix}/manifest.json")
        if manifest_member is None:
            raise ValueError("archive manifest is missing")
        manifest = json.load(manifest_member)
        if manifest.get("format_version") != 1 or manifest.get("corpus_version") != prefix.removeprefix("paper-atlas-corpus-"):
            raise ValueError("archive manifest version mismatch")
        expected_names = {f"{prefix}/manifest.json"}
        for entry in manifest["files"]:
            name = f"{prefix}/{entry['path']}"
            expected_names.add(name)
            member = archive.getmember(name)
            if member.size != entry["bytes"]:
                raise ValueError(f"size mismatch: {entry['path']}")
            stream = archive.extractfile(member)
            digest = hashlib.sha256()
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
            if digest.hexdigest() != entry["sha256"]:
                raise ValueError(f"SHA-256 mismatch: {entry['path']}")
        if set(names) != expected_names:
            raise ValueError("archive has unexpected or missing files")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    builder = subparsers.add_parser("build")
    builder.add_argument("--data-dir", type=Path, required=True)
    builder.add_argument("--output-dir", type=Path, required=True)
    builder.add_argument("--version", required=True)
    checker = subparsers.add_parser("verify")
    checker.add_argument("archive", type=Path)
    args = parser.parse_args()
    if args.command == "build":
        archive_path = build(args.data_dir, args.output_dir, args.version)
        manifest = verify(archive_path)
        print(f"Built {archive_path} ({manifest['paper_count']} papers)")
    else:
        manifest = verify(args.archive)
        print(f"Verified {args.archive} ({manifest['paper_count']} papers)")


if __name__ == "__main__":
    main()
