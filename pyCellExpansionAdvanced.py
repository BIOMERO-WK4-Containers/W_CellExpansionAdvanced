# -*- coding: utf-8 -*-
""" __author__ =  'Ron Hoebe <r.a.hoebe@amsterdamumc.nl>'
    __version__ = '1.01'
    __website__ = 'https://github.com/orgs/Cellular-Imaging-Amsterdam-UMC/repositories'
    __license__ = 'GNU 3.0 license'        
"""

def CellExpansion(imCellsNucleiLabels,maxpixels,discardcellswithoutcytoplasm):
    # -*- coding: utf-8 -*-
    """CellExpansion
        
        Expand Nuclei Labels to Cells with max maxpixels size expansion

        input:
            imCellsNucleiLabels, maxpixels, discardcellswithoutcytoplasm
        output:
            imCellsNucleiLabels, imCellsCellLabels, imCellsCytoplasmLabels

        Be sure to install:
        pip install opencv-python
        pip install numpy
        pip install pykdtree         (for pykdtree.kdtree.KDTree)
        pip install scikit-image     (for skimage.segmentation.relabel_sequential)
        pip install ismember         (for ismember.ismember)
    """
    import cv2
    import numpy as np
    from pykdtree.kdtree import KDTree as pyKDTree
    from skimage.segmentation import relabel_sequential
    from ismember import ismember

    # Distance transform (distance of all black pixel to nearest non black pixel
    ret,imCellsNucleiLabelsBI=cv2.threshold(imCellsNucleiLabels,0,1,cv2.THRESH_BINARY_INV)
    NucleiDist = cv2.distanceTransform(imCellsNucleiLabelsBI.astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)

    # Restrict to maxpixels distance
    NucleiDist[NucleiDist>maxpixels]=0

    # Get Coordinates of all distance transform pixels (x,y)
    NucleiDistCoords=np.argwhere(NucleiDist)

    # Get Coordinates of all Nuclei Labels (x,y)
    LabelCoords=np.argwhere(imCellsNucleiLabels)

    # Search Which Label Coords are Nearest to a distance pixel Coords
    tree=pyKDTree(LabelCoords)
    nearest_ind=tree.query(NucleiDistCoords, k=1)[1]

    # Convert Nearest Label and Pixel Coords (x,y) to indices (number)
    LabelCoordsNN=LabelCoords[nearest_ind]

    # Create Cytoplasm Label with same value as nearest Nucleus Label
    imCellsCytoplasmLabels=np.zeros_like(imCellsNucleiLabels)
    imCellsCytoplasmLabels[NucleiDistCoords[:,0],NucleiDistCoords[:,1]]=imCellsNucleiLabels[(LabelCoordsNN[:,0],LabelCoordsNN[:,1])]
    # Check for nuclei without cytoplasm and remove these nuclei
    # This typically does not happen often, when not used the labels of
    # cytoplasm and nuclei do not match    
    if discardcellswithoutcytoplasm:
        indDiff=np.setdiff1d(imCellsNucleiLabels,imCellsCytoplasmLabels)
        if indDiff.size>0:
            imCellsNucleiLabels[ismember(imCellsNucleiLabels,indDiff)[0]]=0
            imCellsNucleiLabels=relabel_sequential(imCellsNucleiLabels)[0]
            imCellsCytoplasmLabels=relabel_sequential(imCellsCytoplasmLabels)[0]
    imCellsCellLabels=imCellsNucleiLabels+imCellsCytoplasmLabels

    return imCellsNucleiLabels, imCellsCellLabels, imCellsCytoplasmLabels 