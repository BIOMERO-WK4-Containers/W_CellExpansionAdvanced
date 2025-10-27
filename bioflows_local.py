from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import List, Optional, Sequence

CLASS_SPTCNT = "LOCAL_CLASS_SPTCNT"

DEFAULT_INPUT_DIR = os.environ.get("CELL_EXPANSION_INPUT_DIR", "infolder")
DEFAULT_OUTPUT_DIR = os.environ.get("CELL_EXPANSION_OUTPUT_DIR", "outfolder")
DEFAULT_GT_DIR = os.environ.get("CELL_EXPANSION_GT_DIR", "gtfolder")
DEFAULT_TEMP_DIR = os.environ.get(
    "CELL_EXPANSION_TEMP_DIR",
    os.path.join(DEFAULT_OUTPUT_DIR, "tmp"),
)
DEFAULT_SUFFIXES = (
    ".tif",
    ".tiff",
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".npy",
)


@dataclass
class ImageResource:
    """Minimal image representation compatible with the original wrapper."""

    filename: str
    filename_original: str
    filepath: Path

    def __post_init__(self) -> None:
        self.filepath = Path(self.filepath)
        self.path = str(self.filepath)


class BiaflowsJob:
    """Local stand-in for the Cytomine/BIAFLOWS job helper."""

    def __init__(self, args: argparse.Namespace) -> None:
        self.parameters = SimpleNamespace(
            max_pixels=int(args.max_pixels),
            discard_cells_without_cytoplasm=bool(args.discard_cells_without_cytoplasm),
        )
        self.flags = {}
        self.input_dir = Path(args.input_dir)
        self.output_dir = Path(args.output_dir)
        self.gt_dir = Path(args.gt_dir)
        self.temp_dir = Path(args.temp_dir)
        self.suffixes = self._normalise_suffixes(args.suffixes)

    def __enter__(self) -> "BiaflowsJob":
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False

    @classmethod
    def from_cli(cls, argv: Sequence[str]) -> "BiaflowsJob":
        args = _parse_args(argv)
        return cls(args)

    @staticmethod
    def _normalise_suffixes(
        suffixes: Optional[Sequence[str]],
    ) -> Optional[List[str]]:
        if not suffixes:
            return list(DEFAULT_SUFFIXES)
        normalised: List[str] = []
        for suffix in suffixes:
            clean = suffix.strip().lower()
            if not clean:
                continue
            if not clean.startswith("."):
                clean = f".{clean}"
            normalised.append(clean)
        return normalised or list(DEFAULT_SUFFIXES)


def prepare_data(
    discipline: str,
    job: BiaflowsJob,
    *,
    is_2d: bool = True,
    **flags,
):
    """Prepare input/output directories and enumerate available images."""

    del discipline, flags  # Not required for the local implementation
    if not is_2d:
        print("Warning: local workflow only supports 2D data; proceeding regardless.")

    job.input_dir.mkdir(parents=True, exist_ok=True)
    job.output_dir.mkdir(parents=True, exist_ok=True)
    job.temp_dir.mkdir(parents=True, exist_ok=True)

    in_imgs = _collect_images(job.input_dir, job.suffixes)
    gt_imgs = _collect_images(job.gt_dir, job.suffixes)

    return (
        in_imgs,
        gt_imgs,
        str(job.input_dir),
        str(job.gt_dir),
        str(job.output_dir),
        str(job.temp_dir),
    )


def get_discipline(job: BiaflowsJob, default: Optional[str] = None) -> Optional[str]:
    """Return the requested default discipline (placeholder for compatibility)."""

    del job
    return default


def _collect_images(directory: Path, suffixes: Optional[Sequence[str]]) -> List[ImageResource]:
    if not directory.exists():
        return []
    records: List[ImageResource] = []
    for entry in sorted(directory.iterdir()):
        if not entry.is_file():
            continue
        if suffixes and entry.suffix.lower() not in suffixes:
            continue
        records.append(
            ImageResource(
                filename=entry.name,
                filename_original=entry.name,
                filepath=entry,
            )
        )
    return records


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    if _looks_like_legacy(argv):
        return _parse_legacy(argv)
    parser = argparse.ArgumentParser(
        description="Local runner for the Cell Expansion workflow (no Cytomine dependencies)."
    )
    parser.add_argument("--input-dir", dest="input_dir", default=DEFAULT_INPUT_DIR)
    parser.add_argument(
        "--infolder",
        dest="input_dir",
        help="Compatibility alias for --input-dir.",
    )
    parser.add_argument("--output-dir", dest="output_dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--outfolder",
        dest="output_dir",
        help="Compatibility alias for --output-dir.",
    )
    parser.add_argument("--gt-dir", dest="gt_dir", default=DEFAULT_GT_DIR)
    parser.add_argument(
        "--gtfolder",
        dest="gt_dir",
        help="Compatibility alias for --gt-dir.",
    )
    parser.add_argument("--temp-dir", dest="temp_dir", default=DEFAULT_TEMP_DIR)
    parser.add_argument(
        "--tmpfolder",
        dest="temp_dir",
        help="Compatibility alias for --temp-dir.",
    )

    parser.add_argument(
        "--suffix",
        dest="suffixes",
        action="append",
        help="Restrict processing to files matching this extension (can be repeated).",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Compatibility flag ignored by the local runner.",
    )
    parsed = parser.parse_args(argv)
    if parsed.input_dir is None:
        parsed.input_dir = DEFAULT_INPUT_DIR
    if parsed.output_dir is None:
        parsed.output_dir = DEFAULT_OUTPUT_DIR
    if parsed.gt_dir is None:
        parsed.gt_dir = DEFAULT_GT_DIR
    if parsed.temp_dir is None:
        parsed.temp_dir = DEFAULT_TEMP_DIR
    return parsed


def _parse_legacy(argv: Sequence[str]) -> argparse.Namespace:
    max_pixels = int(argv[5])
    discard = _parse_bool(argv[6])
    return argparse.Namespace(
        input_dir=DEFAULT_INPUT_DIR,
        output_dir=DEFAULT_OUTPUT_DIR,
        gt_dir=DEFAULT_GT_DIR,
        temp_dir=DEFAULT_TEMP_DIR,
        max_pixels=max_pixels,
        discard_cells_without_cytoplasm=discard,
        suffixes=list(DEFAULT_SUFFIXES),
    )


def _looks_like_legacy(argv: Sequence[str]) -> bool:
    if len(argv) < 7:
        return False
    first_segment = argv[:7]
    return all(not argument.startswith("--") for argument in first_segment)


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    truthy = {"true", "1", "yes", "y", "on"}
    falsy = {"false", "0", "no", "n", "off"}
    normalised = value.strip().lower()
    if normalised in truthy:
        return True
    if normalised in falsy:
        return False
    raise argparse.ArgumentTypeError("Cannot interpret '%s' as a boolean" % value)
