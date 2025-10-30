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
from label_statistics import compute_label_metrics, save_metrics_csv


def _derive_output_filename(original_filename: str, label_name: str) -> str:
    """Return original filename without extension plus a label-specific suffix."""
    suffix_map = {
        "Cells": "_cell_labels.tif",
        "NucleiLabels": "_nuclei_labels.tif",
        "Cytoplasm": "_cytoplasm_labels.tif",
    }

    try:
        suffix = suffix_map[label_name]
    except KeyError as exc:  # guard against unexpected label names
        raise ValueError(f"Unknown label name '{label_name}'") from exc

    stem = Path(original_filename).stem
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


def _get_int_parameter(
    params: SimpleNamespace,
    name: str,
    *,
    default: int = 0,
    minimum: int | None = None,
) -> int:
    raw_value = getattr(params, name, default)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Parameter '{name}' must be an integer") from exc
    if minimum is not None and value < minimum:
        raise ValueError(
            f"Parameter '{name}' must be >= {minimum}, received {value}"
        )
    return value


def _pairing_key(stem: str, *, is_mask: bool) -> str:
    key = stem.lower().split(".", 1)[0]
    if is_mask and key.endswith("_mask"):
        key = key[: -len("_mask")]

    if "_nuclei" in key:
        key = key.split("_nuclei", 1)[0]

    cleaned = key.rstrip("_")
    if not cleaned:
        cleaned = stem.lower().split(".", 1)[0]
    return cleaned


def main(argv):
    with BiaflowsJob.from_cli(argv) as bj:
        parameters = getattr(bj, "parameters", SimpleNamespace())
        maxpixels = int(_require_parameter(parameters, "max_pixels"))
        discardcellswithoutcytoplasm = bool(
            _require_parameter(parameters, "discard_cells_without_cytoplasm")
        )
        nuclei_channel = _get_int_parameter(
            parameters,
            "nuclei_channel",
            default=0,
            minimum=0,
        )

        print("Initialisation...")

        in_imgs, _, in_path, _, out_path, tmp_path = prepare_data(
            get_discipline(bj, default=CLASS_SPTCNT), bj, is_2d=True, **bj.flags
        )
        tmp_path = os.path.join(tmp_path, "cell_expansion_tmp")
        os.makedirs(tmp_path, exist_ok=True)
        metrics_rows = []

        print(
            f"Parameters: Max pixels: {maxpixels} |"
            f"                Require cyto: {discardcellswithoutcytoplasm} |"
            f"                Nucleus channel: {nuclei_channel}"
        )
        print("Launching workflow...")

        intensity_map = {}
        mask_entries = []
        for bfimg in in_imgs:
            stem = Path(bfimg.filename).stem
            lower_stem = stem.lower()

            if lower_stem.endswith("_cell_labels") or lower_stem.endswith(
                "_cytoplasm_labels"
            ) or lower_stem.endswith("_nuclei_labels"):
                continue

            if "_nuclei_mask" in lower_stem:
                base_key = _pairing_key(lower_stem, is_mask=True)
                if not base_key:
                    print(
                        f"Warning: could not derive pairing key for mask '{bfimg.filename}', skipping."
                    )
                    continue
                mask_entries.append((base_key, bfimg))
                continue

            base_key = _pairing_key(lower_stem, is_mask=False)
            if not base_key:
                print(
                    f"Warning: could not derive pairing key for intensity image '{bfimg.filename}', skipping."
                )
                continue
            if base_key in intensity_map:
                print(
                    f"Warning: multiple intensity images detected for base name '{stem}'."
                    f" Using '{bfimg.filename}'."
                )
            intensity_map[base_key] = bfimg

        if not mask_entries:
            raise ValueError(
                "No nuclei mask images found (expected filenames containing '_nuclei_mask',"
                " e.g. 'sample_nuclei_mask.ome.tif')."
            )

        processed_imgs = []
        matched_intensity_keys = set()

        for base_key, bfimg in mask_entries:
            print(f"CellExpand: {bfimg.__dict__}")
            fn = os.path.join(in_path, bfimg.filename)
            imCellsNucleiLabels = imageio.imread(fn)
            if imCellsNucleiLabels.ndim == 3:
                imCellsNucleiLabels = skimage.color.rgb2gray(imCellsNucleiLabels)

            if imCellsNucleiLabels.ndim != 2:
                raise ValueError(
                    f"Input image {bfimg.filename} has too many channels for a nuclei mask"
                )

            intensity_img = intensity_map.get(base_key)
            if intensity_img is None:
                raise ValueError(
                    f"Could not find intensity image matching mask '{bfimg.filename}'"
                )

            intensity_path = os.path.join(in_path, intensity_img.filename)
            intensity_reference = imageio.imread(intensity_path)

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

            metrics_rows.extend(
                compute_label_metrics(
                    intensity_img.filename,
                    output_arrays,
                    intensity_image=intensity_reference,
                    nuclei_channel=nuclei_channel,
                )
            )
            processed_imgs.append(bfimg)
            matched_intensity_keys.add(base_key)

        unmatched_images = [
            img for key, img in intensity_map.items() if key not in matched_intensity_keys
        ]
        if unmatched_images:
            remaining = ", ".join(sorted(img.filename for img in unmatched_images))
            print(
                f"Warning: intensity images without matching nuclei mask were ignored: {remaining}"
            )

        for bimg in processed_imgs:
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

        csv_path = save_metrics_csv(out_path, metrics_rows)
        if csv_path:
            print(f"Saved metrics table to {csv_path}")

        _clear_directory(tmp_path, remove_root=True)
        _remove_if_empty(os.path.dirname(tmp_path))
        print("Finished.")


if __name__ == "__main__":
    main(sys.argv[1:])