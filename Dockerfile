FROM python:3.12.7-bookworm

# ------------------------------------------------------------------------------
# Install workflow dependencies only
RUN pip install --no-cache-dir \
    numpy==2.0.1 \
    opencv-python-headless==4.10.0.84 \
    pandas==2.2.2 \
    scikit-image==0.24.0 \
    imagecodecs==2024.6.1 \
    scipy==1.14.1 \
    ismember==1.0.2

WORKDIR /app

ADD bioflows_local.py /app/bioflows_local.py
ADD wrapper.py /app/wrapper.py
ADD pyCellExpansionAdvanced.py /app/pyCellExpansionAdvanced.py
ADD label_statistics.py /app/label_statistics.py
ADD descriptor.json /app/descriptor.json

ENTRYPOINT ["python3.12", "/app/wrapper.py"]
