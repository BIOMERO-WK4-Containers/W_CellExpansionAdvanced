FROM python:3.7-bullseye

# ------------------------------------------------------------------------------
# Install Cytomine python client
RUN git clone https://github.com/cytomine-uliege/Cytomine-python-client.git && \
    cd /Cytomine-python-client && git checkout tags/v2.7.3 && pip install . && \
    rm -r /Cytomine-python-client

# ------------------------------------------------------------------------------
# Install BIAFLOWS utilities (annotation exporter, compute metrics, helpers,...)
RUN apt-get update && apt-get install libgeos-dev -y && apt-get clean
RUN git clone https://github.com/Neubias-WG5/biaflows-utilities.git && \
    cd /biaflows-utilities/ && git checkout tags/v0.9.2 && pip install .

# install utilities binaries
RUN chmod +x /biaflows-utilities/bin/*
RUN cp /biaflows-utilities/bin/* /usr/bin/ && \
    rm -r /biaflows-utilities

# ------------------------------------------------------------------------------
# Install workflow dependencies
RUN pip install opencv-python-headless==4.5.5.64 \
    pykdtree==1.3.7.post0 \
    scikit-image==0.19.3 \
    ismember==1.0.2 \
    numpy==1.20.1 \
    pandas==1.3.5 \
    imagecodecs

ADD wrapper.py /app/wrapper.py
# for running the wrapper locally
ADD pyCellExpansion.py /app/pyCellExpansion.py
ADD descriptor.json /app/descriptor.json

ENTRYPOINT ["python3.7","/app/wrapper.py"]
