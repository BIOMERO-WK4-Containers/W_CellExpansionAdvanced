"""Utilities for summarising label intensity metrics."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence

import numpy as np
from skimage.measure import regionprops_table

DEFAULT_FIELDNAMES = (
    "image",
    "label_type",
    "label_id",
    "nuclei_channel",
    "nuclei_channel_label",
    "mean_intensity",
    "max_intensity",
    "variance_intensity",
    "summed_intensity",
    "area",
    "perimeter",
    "eccentricity",
    "solidity",
    "major_axis_length",
    "minor_axis_length",
    "equivalent_diameter",
    "centroid_row",
    "centroid_col",
)


def compute_label_metrics(
    image_name: str,
    label_arrays: Mapping[str, np.ndarray],
    *,
    intensity_image: Optional[np.ndarray] = None,
    nuclei_channel: int = 0,
    channel_names: Optional[Sequence[str]] = None,
) -> List[Dict[str, float]]:
    """Collect per-label intensity and morphology statistics.

    Parameters
    ----------
    image_name: str
        Name of the source image for traceability in the output table.
    label_arrays: Mapping[str, np.ndarray]
        Mapping of label names to their mask arrays (integer labelled images).
    intensity_image: Optional[np.ndarray]
        Optional intensity image used to extract per-channel statistics. When
        omitted the label image itself is used as the intensity source.
    nuclei_channel: int
        Zero-based channel index that should be treated as the nucleus channel
        when populating the summarised intensity columns.
    channel_names: Optional[Sequence[str]]
        Optional human-readable labels for each channel in the intensity image.

    Returns
    -------
    List[Dict[str, float]]
        One row per labelled object per label type containing summary statistics.
    """

    rows: List[Dict[str, float]] = []
    shared_intensity_stack: Optional[np.ndarray] = None
    shared_channel_labels: Optional[List[str]] = None
    warned_nuclei_channel = False

    for label_name, data in label_arrays.items():
        if data is None:
            continue

        arr = np.asarray(data)
        if arr.ndim != 2:
            raise ValueError(
                f"Expected 2-D label array for '{label_name}', got shape {arr.shape}"
            )

        if intensity_image is not None:
            if shared_intensity_stack is None:
                (
                    shared_intensity_stack,
                    shared_channel_labels,
                ) = _prepare_intensity_stack(intensity_image, arr.shape, channel_names)
            elif shared_intensity_stack.shape[1:] != arr.shape:
                raise ValueError(
                    "Intensity image dimensions do not match label dimensions"
                )
            intensity_stack = shared_intensity_stack
            channel_labels = shared_channel_labels or []
        else:
            intensity_stack = arr[np.newaxis, ...]
            channel_labels = ["mask"]

        labels_present = np.unique(arr)
        labels_present = labels_present[labels_present != 0]
        if not labels_present.size:
            continue

        props = regionprops_table(
            arr,
            properties=(
                "label",
                "area",
                "perimeter",
                "eccentricity",
                "solidity",
                "major_axis_length",
                "minor_axis_length",
                "equivalent_diameter",
                "centroid",
            ),
        )

        channel_count = len(channel_labels)
        if channel_count == 0:
            continue
        nuc_index = min(max(nuclei_channel, 0), channel_count - 1)
        if not warned_nuclei_channel and nuc_index != nuclei_channel:
            print(
                f"Warning: nuclei_channel {nuclei_channel} out of range for image '{image_name}'. "
                f"Using channel index {nuc_index} instead."
            )
            warned_nuclei_channel = True
        nuc_label = channel_labels[nuc_index]

        for idx, label_id in enumerate(props["label"]):
            region_mask = arr == label_id

            channel_metrics: Dict[str, float] = {}
            for channel_idx, channel_label in enumerate(channel_labels):
                channel_values = intensity_stack[channel_idx][region_mask]
                channel_values = channel_values.astype(float, copy=False)
                if channel_values.size:
                    channel_metrics[f"mean_intensity_{channel_label}"] = float(
                        channel_values.mean()
                    )
                    channel_metrics[f"max_intensity_{channel_label}"] = float(
                        channel_values.max()
                    )
                    channel_metrics[f"variance_intensity_{channel_label}"] = float(
                        channel_values.var()
                    )
                    channel_metrics[f"summed_intensity_{channel_label}"] = float(
                        channel_values.sum()
                    )
                else:
                    channel_metrics[f"mean_intensity_{channel_label}"] = 0.0
                    channel_metrics[f"max_intensity_{channel_label}"] = 0.0
                    channel_metrics[f"variance_intensity_{channel_label}"] = 0.0
                    channel_metrics[f"summed_intensity_{channel_label}"] = 0.0

            row = {
                "image": image_name,
                "label_type": label_name,
                "label_id": int(label_id),
                "nuclei_channel": nuc_index,
                "nuclei_channel_label": nuc_label,
                "mean_intensity": channel_metrics[f"mean_intensity_{nuc_label}"],
                "max_intensity": channel_metrics[f"max_intensity_{nuc_label}"],
                "variance_intensity": channel_metrics[
                    f"variance_intensity_{nuc_label}"
                ],
                "summed_intensity": channel_metrics[
                    f"summed_intensity_{nuc_label}"
                ],
                "area": float(props["area"][idx]),
                "perimeter": float(props["perimeter"][idx]),
                "eccentricity": float(props["eccentricity"][idx]),
                "solidity": float(props["solidity"][idx]),
                "major_axis_length": float(props["major_axis_length"][idx]),
                "minor_axis_length": float(props["minor_axis_length"][idx]),
                "equivalent_diameter": float(props["equivalent_diameter"][idx]),
                "centroid_row": float(props["centroid-0"][idx]),
                "centroid_col": float(props["centroid-1"][idx]),
            }
            row.update(channel_metrics)
            rows.append(row)

    return rows


def _prepare_intensity_stack(
    intensity_image: np.ndarray,
    label_shape: Sequence[int],
    channel_names: Optional[Sequence[str]] = None,
) -> tuple[np.ndarray, List[str]]:
    arr = np.asarray(intensity_image)
    if arr.ndim == 2:
        if arr.shape != tuple(label_shape):
            raise ValueError("Intensity image does not match label shape")
        stack = arr[np.newaxis, ...]
    elif arr.ndim == 3:
        if arr.shape[:2] == tuple(label_shape):
            stack = np.moveaxis(arr, -1, 0)
        elif arr.shape[-2:] == tuple(label_shape):
            stack = arr
        else:
            raise ValueError("Cannot align intensity image with label shape")
    else:
        raise ValueError("Intensity image must be 2-D or 3-D")

    channel_count = stack.shape[0]
    if channel_names is not None:
        if len(channel_names) != channel_count:
            raise ValueError(
                "Number of channel names does not match intensity channels"
            )
        labels = _normalise_channel_labels(channel_names)
    else:
        labels = [f"ch{idx}" for idx in range(channel_count)]

    return stack, labels


def _normalise_channel_labels(names: Sequence[str]) -> List[str]:
    labels: List[str] = []
    seen = set()
    for idx, name in enumerate(names):
        clean = _slugify_channel_name(name)
        if not clean or clean in seen:
            clean = f"ch{idx}"
        labels.append(clean)
        seen.add(clean)
    return labels


def _slugify_channel_name(name: str) -> str:
    cleaned = name.strip().lower().replace(" ", "_")
    safe = [ch if ch.isalnum() or ch == "_" else "_" for ch in cleaned]
    result = "".join(safe).strip("_")
    return result


def save_metrics_csv(
    output_directory: str,
    rows: List[Dict[str, float]],
    *,
    filename: str = "label_metrics.csv",
    fieldnames: Optional[Sequence[str]] = None,
) -> Optional[Path]:
    """Persist collected metrics to a CSV file.

    Returns the path to the written file, or ``None`` if ``rows`` is empty.
    """

    if not rows:
        return None

    if fieldnames is None:
        header = list(DEFAULT_FIELDNAMES)
    else:
        header = list(fieldnames)
    for row in rows:
        for key in row.keys():
            if key not in header:
                header.append(key)

    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    csv_path = output_path / filename

    with open(csv_path, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)

    return csv_path
