import sys
import os
import shutil
import imageio
import numpy as np
import skimage
from biaflows import CLASS_SPTCNT
from biaflows.helpers import BiaflowsJob, prepare_data, get_discipline
# code for workflow:
from pyCellExpansion import CellExpansion


def main(argv):
    with BiaflowsJob.from_cli(argv) as bj:
        
        print("Initialisation...")

        # 1. Prepare data for workflow
        # 1a. Get folders
        in_imgs, gt_imgs, in_path, gt_path, out_path, tmp_path = prepare_data(
            get_discipline(bj, default=CLASS_SPTCNT), bj, is_2d=True, **bj.flags)
        # 1b. MAKE SURE TMP PATH IS UNIQUE
        tmp_path = gt_path
        # 1c. Read parameters from commandline
        maxpixels = bj.parameters.max_pixels
        discardcellswithoutcytoplasm = bj.parameters.discard_cells_without_cytoplasm
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
            # Write intermediate results
            imageio.imwrite(
                os.path.join(tmp_path,
                             bfimg.filename.replace("Nuclei", "Cells")),
                imCellsCellLabels)
            print(f"Wrote expanded cell mask to {tmp_path}")

        # 2b. Copy to out folder when we're done
        for bimg in in_imgs:
            shutil.copy(
                os.path.join(tmp_path, 
                             bimg.filename.replace("Nuclei", "Cells")),
                out_path)
            print(f"Copied tmp files to {out_path}")

        # 3. Pipeline finished
        # 3a. cleanup tmp
        shutil.rmtree(tmp_path)  
        print("Finished.")


if __name__ == "__main__":
    main(sys.argv[1:])
