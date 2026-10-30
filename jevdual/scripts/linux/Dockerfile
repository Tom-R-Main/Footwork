# Task-owned Linux builder/desktop. Build requires approval for network installations.
# The base is an already cached ExecuFunction workspace, not a new cloud allocation.
ARG BASE_IMAGE=412268502261.dkr.ecr.us-east-1.amazonaws.com/execufunction-agent-runtime-workspace:journey-base-cccffcb67e43
FROM ${BASE_IMAGE}
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl python3-venv python3-pip python3-dev \
    clang cmake pkg-config libdbus-1-dev libx11-dev libxi-dev libxtst-dev \
    libxext-dev libwayland-dev libxkbcommon-dev libssl-dev \
    dbus-x11 at-spi2-core openbox mousepad xauth \
    && rm -rf /var/lib/apt/lists/*
USER workspace
ENV PATH="/home/workspace/.cargo/bin:/home/workspace/.local/bin:${PATH}"
RUN python3 -m venv /home/workspace/footwork-build-tools \
    && /home/workspace/footwork-build-tools/bin/python -m pip install --only-binary=:all: uv==0.12.5
ENV PATH="/home/workspace/footwork-build-tools/bin:${PATH}"
RUN curl --proto '=https' --tlsv1.2 --fail --silent --show-error \
    https://sh.rustup.rs -o /home/workspace/rustup-init.sh \
    && sh /home/workspace/rustup-init.sh -y --profile minimal --default-toolchain 1.97.1 \
    && rm /home/workspace/rustup-init.sh
# Keep the native source hook's existing two-job build within a small memory budget.
ENV CARGO_BUILD_JOBS=2
WORKDIR /workspace
ENTRYPOINT ["/bin/bash"]
