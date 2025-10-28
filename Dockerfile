FROM python:3.13.9-trixie

# ------------------------------------------------------------------------------
# Install workflow dependencies only
RUN pip install --no-cache-dir \
    numpy==2.0.1 \
    opencv-python-headless==4.10.0.84 \
    pandas==2.2.3 \
    scikit-image==0.24.0 \
    imagecodecs==2024.6.1 \
    pykdtree==1.3.12 \
    ismember==1.0.2

WORKDIR /app

ADD bioflows_local.py /app/bioflows_local.py
ADD wrapper.py /app/wrapper.py
ADD pyCellExpansionAdvanced.py /app/pyCellExpansionAdvanced.py
ADD descriptor.json /app/descriptor.json

ENTRYPOINT ["python3.13", "/app/wrapper.py"]
