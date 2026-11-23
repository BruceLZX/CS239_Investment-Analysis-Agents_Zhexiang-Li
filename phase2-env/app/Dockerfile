# policy-portin:batch-v1 plus this app's dependencies, for `policyweave port --image`. The check containers run
# without a network, so everything the app imports is installed here (mcp 2.1.1 replaces the image's 1.30.0).
FROM policy-portin:batch-v1
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libharfbuzz-subset0 libfontconfig1 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/app-requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/app-requirements.txt && rm /tmp/app-requirements.txt
ENTRYPOINT []
