# PolicyWeave's src/policyweave/adapters/Dockerfile for arm64. The only change: the framework adds the official
# x86_64 Soufflé 2.5 package, and this copies the same release built from source for arm64 (see ../Dockerfile.host).
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends libffi8 libgomp1 libncurses6 libtinfo6 libsqlite3-0 libstdc++6 libgcc-s1 zlib1g util-linux mcpp \
    && rm -rf /var/lib/apt/lists/*
COPY souffle /opt/souffle
ENV PATH="/opt/souffle/usr/bin:${PATH}" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY src/policyweave /framework/policyweave
ENV PYTHONPATH=/framework
WORKDIR /tmp
USER 65534:65534
CMD ["souffle", "--version"]
