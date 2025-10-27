FROM python:3.7-bullseye

# ------------------------------------------------------------------------------
# Install workflow dependencies only
RUN pip install --no-cache-dir \
    opencv-python-headless==4.5.5.64 \
    pykdtree==1.3.7.post0 \
    scikit-image==0.19.3 \
    ismember==1.0.2 \
    numpy==1.20.1 \
    pandas==1.3.5 \
    imagecodecs

WORKDIR /app

ADD bioflows_local.py /app/bioflows_local.py
ADD wrapper.py /app/wrapper.py
ADD pyCellExpansionAdvanced.py /app/pyCellExpansionAdvanced.py
ADD descriptor.json /app/descriptor.json

ENTRYPOINT ["python3.7", "/app/wrapper.py"]
