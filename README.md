# W_CellExpansion

Workflow for Cell Expansion, algorithm by Ron Hoebe, Amsterdam UMC.

In descriptor.json (do not use tag (v1.0.1) here)

  "name": "CellExpansionAdvanced",
  "description": "2D Cell Expansion of Nuceli Annotations with advanced options",
  "container-image": {
    "image": "cellularimagingcf/w_cellexpansionadvanced",
    "type": "singularity"
  },

On github create a release with the tag (v1.0.1) 


# Build docker and tag and push

docker build -t w_cellexpansionadvanced .

docker tag w_cellexpansionadvanced cellularimagingcf/w_cellexpansionadvanced:v1.0.1
docker push cellularimagingcf/w_cellexpansionadvanced:v1.0.1

docker tag w_cellexpansionadvanced cellularimagingcf/w_cellexpansionadvanced:latest
docker push cellularimagingcf/w_cellexpansionadvanced:latest


To test the docket locally do:

docker run --rm ^
	-v "%DATA_PATH%\infolder:/data/in" ^
	-v "%DATA_PATH%\outfolder:/data/out" ^
	-v "%DATA_PATH%\gtfolder:/data/gt" ^
	w_cellexpansionadvanced ^
	--infolder /data/in ^
	--outfolder /data/out ^
	--gtfolder /data/gt ^
	--local ^
	


License: GNU 3.0 (copyleft)
"# W_CellExpansionAdvanced" 
