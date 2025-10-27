# CellExpansionAdvanced

Containerised workflow for 2D cell expansion segmentation, based on the algorithm by Ron Hoebe (Amsterdam UMC). The pipeline takes a labelled nuclei mask and produces three aligned masks: nuclei, cytoplasm, and whole-cell labels.

## Repository Layout

- `wrapper.py` – BIAFLOWS entry point that orchestrates IO and calls the expansion logic.
- `pyCellExpansionAdvanced.py` – Implementation of the cell expansion algorithm.
- `Dockerfile` – Build instructions for the Docker/Singularity image.
- `descriptor.json` – BIAFLOWS/Cytomine app descriptor.
- `run.cmd` – Convenience script to run the container locally on Windows.
- `infolder`, `gtfolder`, `outfolder` – Sample mount points for local testing.

## Building the Container

```cmd
docker build -t w_cellexpansionadvanced .
```

Tag additional versions as required, for example:

```cmd
docker tag yourdockerhub/w_cellexpansionadvanced:v1.0.1
docker push yourdockerhub/w_cellexpansionadvanced:v1.0.1
docker tag yourdockerhub/w_cellexpansionadvanced:latest
docker push yourdockerhub/w_cellexpansionadvanced:latest
```

Ensure `descriptor.json` references the same registry path when publishing a release.

## Local Execution

Place test inputs in `infolder`, optional ground truth in `gtfolder`, and run either the helper script or Docker directly.

### Using `run.cmd`

```cmd
run --max_pixels 30 --discard_cells_without_cytoplasm true
```

The script mounts the three folders under `/data/{in,out,gt}` and forwards any additional parameters to the container. Override the image by setting `IMAGE` before running the script.

### Direct Docker Call

```cmd
set DATA_PATH=C:\path\to\W_CellExpansionAdvanced
docker run --rm ^
    -v "%DATA_PATH%\infolder:/data/in" ^
    -v "%DATA_PATH%\outfolder:/data/out" ^
    -v "%DATA_PATH%\gtfolder:/data/gt" ^
    yourdockerhub/w_cellexpansionadvanced:latest ^
    --infolder /data/in ^
    --outfolder /data/out ^
    --gtfolder /data/gt ^
    --local ^
    --max_pixels 30 ^
    --discard_cells_without_cytoplasm true
```

Outputs are written to `/data/out` (locally `outfolder`) as TIFF masks for Cells, NucleiLabels, and Cytoplasm.

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--max_pixels` | Maximum expansion distance (in pixels) for growing nuclei into cells. | `25` |
| `--discard_cells_without_cytoplasm` | If `true`, removes nuclei that fail to produce cytoplasm labels. | `true` |
| `--local` | Instructs the wrapper to use local folders instead of Cytomine download/upload. | `flag` |

All other Cytomine-related parameters are injected automatically when the workflow runs inside BIAFLOWS/Cytomine.

## Publishing to Cytomine/BIAFLOWS

1. Build and push the container image to the configured registry.
2. Update `descriptor.json` with the new tag if needed.
3. Create a GitHub release (e.g., `v1.0.1`) pointing to the descriptor for reproducibility.
4. Register the application in BIOMERO/Cytomine using the release URL.

## License

GNU General Public License v3.0
