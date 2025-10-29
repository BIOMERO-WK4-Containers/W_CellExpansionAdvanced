import os
import shutil
import sys
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
    """Create an output filename by replacing the Nuclei token when present."""
    if "Nuclei" in original_filename:
        return original_filename.replace("Nuclei", label_name)
    name, ext = os.path.splitext(original_filename)
    return f"{name}_{label_name}{ext}"


def _clear_directory(directory: str) -> None:
    """Remove all content inside directory without deleting the directory itself."""
    if not os.path.isdir(directory):
        return
    for entry in os.scandir(directory):
        try:
            if entry.is_dir(follow_symlinks=False):
                shutil.rmtree(entry.path, ignore_errors=True)
            else:
                os.remove(entry.path)
        except OSError as exc:  # keep going if a file is busy
            print(f"Warning: could not remove {entry.path}: {exc}")


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

        _clear_directory(tmp_path)
        print("Finished.")


if __name__ == "__main__":
    main(sys.argv[1:])