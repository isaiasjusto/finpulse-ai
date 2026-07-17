FROM jupyter/scipy-notebook@sha256:fca4bcc9cbd49d9a15e0e4df6c666adf17776c950da9fa94a4f0a045d5c4ad33

COPY requirements.txt /tmp/requirements.txt

RUN pip install \
    --no-cache-dir \
    --requirement /tmp/requirements.txt

WORKDIR /home/jovyan/work