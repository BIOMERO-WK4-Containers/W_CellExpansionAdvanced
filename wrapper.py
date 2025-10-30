import os
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import imageio.v2 as imageio
import skimage

from bioflows_local import (
    CLASS_SPTCNT,
    BiaflowsJob,
    get_discipline,
    prepare_data,
)
from pyCellExpansionAdvanced import CellExpansion


def _derive_output_filename(original_filename: str, label_name: str) -> str:
    """Return original base filename with a label-specific suffix."""
    suffix_map = {
        "Cells": "_cell_labels.tif",
        "NucleiLabels": "_nuclei_labels.tif",
        "Cytoplasm": "_cytoplasm_labels.tif",
    }

    try:
        suffix = suffix_map[label_name]
    except KeyError as exc:  # guard against unexpected label names
        raise ValueError(f"Unknown label name '{label_name}'") from exc

    suffixes = "".join(Path(original_filename).suffixes)
    stem = original_filename[: -len(suffixes)] if suffixes else original_filename
    return f"{stem}{suffix}"


def _clear_directory(directory: str, *, remove_root: bool = False) -> None:
    """Remove all content inside directory and optionally delete the directory."""
    path = Path(directory)
    if not path.is_dir():
        return

    if remove_root:
        try:
            shutil.rmtree(path)
        except OSError as exc:
            print(f"Warning: could not remove directory {directory}: {exc}")
        return

    for entry in path.iterdir():
        try:
            if entry.is_dir():
                shutil.rmtree(entry, ignore_errors=True)
            else:
                entry.unlink()
        except OSError as exc:  # keep going if a file is busy
            print(f"Warning: could not remove {entry}: {exc}")


def _remove_if_empty(directory: str) -> None:
    """Attempt to remove directory if it exists and is empty."""
    path = Path(directory)
    if not path.is_dir():
        return
    try:
        path.rmdir()
    except OSError:
        pass


def _require_parameter(params: SimpleNamespace, name: str):
    value = getattr(params, name, None)
    if value is None:
        raise ValueError(f"Missing required parameter '{name}'")
    return value


def main(argv):
    with BiaflowsJob.from_cli(argv) as bj:
        parameters = getattr(bj, "parameters", SimpleNamespace())
        maxpixels = int(_require_parameter(parameters, "max_pixels"))
        discardcellswithoutcytoplasm = bool(
            _require_parameter(parameters, "discard_cells_without_cytoplasm")
        )

        print("Initialisation...")

        in_imgs, _, in_path, _, out_path, tmp_path = prepare_data(
            get_discipline(bj, default=CLASS_SPTCNT), bj, is_2d=True, **bj.flags
        )
        tmp_path = os.path.join(tmp_path, "cell_expansion_tmp")
        os.makedirs(tmp_path, exist_ok=True)

        print(
            f"Parameters: Max pixels: {maxpixels} |"
            f"                Require cyto: {discardcellswithoutcytoplasm}"
        )
        print("Launching workflow...")

        for bfimg in in_imgs:
            print(f"CellExpand: {bfimg.__dict__}")
            fn = os.path.join(in_path, bfimg.filename)
            imCellsNucleiLabels = imageio.imread(fn)
            if imCellsNucleiLabels.ndim == 3:
                # we will assume x,y,c and not c,x,y.
                imCellsNucleiLabels = skimage.color.rgb2gray(imCellsNucleiLabels)

            if imCellsNucleiLabels.ndim != 2:
                raise ValueError(
                    f"Input image {bfimg} has too many channels for a Nuclei mask!"
                )

            (
                imCellsNucleiLabels,
                imCellsCellLabels,
                imCellsCytoplasmLabels,
            ) = CellExpansion(
                imCellsNucleiLabels=imCellsNucleiLabels,
                discardcellswithoutcytoplasm=discardcellswithoutcytoplasm,
                maxpixels=maxpixels,
            )

            output_arrays = {
                "Cells": imCellsCellLabels,
                "NucleiLabels": imCellsNucleiLabels,
                "Cytoplasm": imCellsCytoplasmLabels,
            }
            for label_name, data in output_arrays.items():
                output_filename = _derive_output_filename(bfimg.filename, label_name)
                imageio.imwrite(os.path.join(tmp_path, output_filename), data)
                print(f"Wrote {label_name} mask to {tmp_path}")

        for bimg in in_imgs:
            for label_name in ("Cells", "NucleiLabels", "Cytoplasm"):
                src_path = os.path.join(
                    tmp_path,
                    _derive_output_filename(bimg.filename, label_name),
                )
                if os.path.exists(src_path):
                    shutil.copy(src_path, out_path)
                    print(f"Copied {label_name} mask to {out_path}")
                else:
                    print(
                        f"Warning: expected {label_name} mask missing for {bimg.filename}"
                    )
        _clear_directory(tmp_path, remove_root=True)
        _remove_if_empty(os.path.dirname(tmp_path))
        print("Finished.")


if __name__ == "__main__":
    main(sys.argv[1:])