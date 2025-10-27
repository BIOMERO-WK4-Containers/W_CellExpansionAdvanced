import argparse
import sys
import os
import shutil
from types import SimpleNamespace
from typing import List, Sequence, Tuple

import imageio.v2 as imageio
import numpy as np
import skimage
from bioflows_local import CLASS_SPTCNT, BiaflowsJob, prepare_data, get_discipline
# code for workflow:
from pyCellExpansionAdvanced import CellExpansion

DEFAULT_MAX_PIXELS = 25
DEFAULT_DISCARD_WITHOUT_CYTOPLASM = True

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
            
def _parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    truthy = {"true", "1", "yes", "y", "on"}
    falsy = {"false", "0", "no", "n", "off"}
    normalised = value.strip().lower()
    if normalised in truthy:
        return True
    if normalised in falsy:
        return False
    raise argparse.ArgumentTypeError(f"Cannot interpret '{value}' as a boolean.")


def _parse_cli_args(argv: Sequence[str]) -> Tuple[argparse.Namespace, List[str]]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--max-pixels", "--max_pixels", dest="max_pixels", type=int)
    parser.add_argument(
        "--discard-cells-without-cytoplasm",
        "--discard_cells_without_cytoplasm",
        dest="discard_cells_without_cytoplasm",
        type=_parse_bool,
    )
    args, remaining = parser.parse_known_args(argv)
    if args.max_pixels is None:
        args.max_pixels = DEFAULT_MAX_PIXELS
    if args.discard_cells_without_cytoplasm is None:
        args.discard_cells_without_cytoplasm = DEFAULT_DISCARD_WITHOUT_CYTOPLASM
    return args, list(remaining)

def main(argv):
    overrides, remaining = _parse_cli_args(argv)
    parameters = SimpleNamespace(
        max_pixels=int(overrides.max_pixels),
        discard_cells_without_cytoplasm=bool(
            overrides.discard_cells_without_cytoplasm
        ),
    )
    with BiaflowsJob.from_cli(remaining, parameters=parameters) as bj:
        maxpixels = parameters.max_pixels
        discardcellswithoutcytoplasm = parameters.discard_cells_without_cytoplasm
        
        print("Initialisation...")

        # 1. Prepare data for workflow
        # 1a. Get folders
        in_imgs, gt_imgs, in_path, gt_path, out_path, tmp_path = prepare_data(
            get_discipline(bj, default=CLASS_SPTCNT), bj, is_2d=True, **bj.flags)
        # 1b. Ensure we have a dedicated temporary directory scoped to this run
        tmp_path = os.path.join(tmp_path, "cell_expansion_tmp")
        os.makedirs(tmp_path, exist_ok=True)
    # 1c. Read parameters from commandline
        print(f"Parameters: Max pixels: {maxpixels} |\
                Require cyto: {discardcellswithoutcytoplasm}")

        # 2. Run image analysis workflow
        print("Launching workflow...")

        # 2a. Add here the code for running the analysis script
        for bfimg in in_imgs:
            print(f"CellExpand: {bfimg.__dict__}")
            # Read Nuclei labels
            fn = os.path.join(in_path, bfimg.filename)
            imCellsNucleiLabels = imageio.imread(fn)
            # Flatten (x,y,c) to (x,y) if needed
            if imCellsNucleiLabels.ndim == 3:
                # we will assume x,y,c and not c,x,y.
                # imCellsNucleiLabels = imCellsNucleiLabels.sum(axis=2)
                imCellsNucleiLabels = skimage.color.rgb2gray(imCellsNucleiLabels)
            
            if imCellsNucleiLabels.ndim != 2:
                raise ValueError(f"Input image {bfimg} has too many channels for a Nuclei mask!")
            
            # Expand Cells
            (imCellsNucleiLabels,
                imCellsCellLabels,
                imCellsCytoplasmLabels) = CellExpansion(
                imCellsNucleiLabels=imCellsNucleiLabels,
                discardcellswithoutcytoplasm=discardcellswithoutcytoplasm,
                maxpixels=maxpixels)
            # Write intermediate results for nuclei, cell, and cytoplasm labels
            output_arrays = {
                "Cells": imCellsCellLabels,
                "NucleiLabels": imCellsNucleiLabels,
                "Cytoplasm": imCellsCytoplasmLabels,
            }
            for label_name, data in output_arrays.items():
                output_filename = _derive_output_filename(bfimg.filename, label_name)
                imageio.imwrite(os.path.join(tmp_path, output_filename), data)
                print(f"Wrote {label_name} mask to {tmp_path}")

        # 2b. Copy to out folder when we're done
        for bimg in in_imgs:
            for label_name in ("Cells", "NucleiLabels", "Cytoplasm"):
                src_path = os.path.join(
                    tmp_path,
                    _derive_output_filename(bimg.filename, label_name))
                if os.path.exists(src_path):
                    shutil.copy(src_path, out_path)
                    print(f"Copied {label_name} mask to {out_path}")
                else:
                    print(f"Warning: expected {label_name} mask missing for {bimg.filename}")

        # 3. Pipeline finished
        # 3a. cleanup tmp
        _clear_directory(tmp_path)
        print("Finished.")


if __name__ == "__main__":
    main(sys.argv[1:])