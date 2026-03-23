# syntax=docker/dockerfile:1.7

ARG UBUNTU_VERSION=24.04
ARG REPO_BASE_IMAGE=cpp-devcontainer-repo-base:dev
ARG FINAL_BASE_IMAGE=cpp-devcontainer-base:dev
ARG CLANG_IMAGE=cpp26-dev-clang:dev
ARG GCC_IMAGE=cpp26-dev-gcc:dev

FROM ubuntu:${UBUNTU_VERSION} AS repo_base

ARG DEBIAN_FRONTEND=noninteractive
ARG NODE_VERSION=25.8.1
ARG NODE_MAJOR=25
ARG MISE_VERSION=v2026.3.10
ARG UV_VERSION=0.10.12
ARG PIXI_VERSION=v0.66.0
ARG LLVM_VERSION=22.1.1
ARG LLVM_ARCHIVE=LLVM-22.1.1-Linux-X64.tar.xz
ARG LLVM_DOWNLOAD_URL=https://github.com/llvm/llvm-project/releases/download/llvmorg-22.1.1/LLVM-22.1.1-Linux-X64.tar.xz
ARG VCPKG_BUNDLE_URL=https://github.com/microsoft/vcpkg-tool/releases/latest/download/vcpkg-standalone-bundle.tar.gz

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      gnupg && \
    install -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
      gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "${VERSION_CODENAME}") stable" \
      >/etc/apt/sources.list.d/docker.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      bash-completion \
      bear \
      build-essential \
      ccache \
      cmake \
      cppcheck \
      docker-buildx-plugin \
      docker-ce-cli \
      fd-find \
      gdb \
      git \
      git-lfs \
      graphviz \
      jq \
      lcov \
      libssl-dev \
      linux-tools-generic \
      lldb \
      locales \
      mold \
      ninja-build \
      pkg-config \
      python3 \
      python3-pip \
      ripgrep \
      rsync \
      shellcheck \
      sudo \
      time \
      unzip \
      valgrind \
      wget \
      xz-utils \
      zip \
      zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --break-system-packages --no-cache-dir conan==2.*

RUN mkdir -p /opt/vcpkg && \
    curl -fsSL "${VCPKG_BUNDLE_URL}" | tar -xzf - --strip-components=1 -C /opt/vcpkg

RUN curl -fsSL "${LLVM_DOWNLOAD_URL}" -o "/tmp/${LLVM_ARCHIVE}" && \
    mkdir -p /opt/llvm && \
    tar -C /opt -xf "/tmp/${LLVM_ARCHIVE}" && \
    mv "/opt/${LLVM_ARCHIVE%.tar.xz}" "/opt/llvm/${LLVM_VERSION}" && \
    ln -sfn "/opt/llvm/${LLVM_VERSION}" /opt/llvm/current && \
    rm -f "/tmp/${LLVM_ARCHIVE}"

RUN curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" \
      -o /tmp/node.tar.xz && \
    mkdir -p "/opt/node/${NODE_VERSION}" && \
    tar -C "/opt/node/${NODE_VERSION}" --strip-components=1 -xf /tmp/node.tar.xz && \
    rm -f /tmp/node.tar.xz && \
    ln -sf "/opt/node/${NODE_VERSION}/bin/node" /usr/local/bin/node && \
    ln -sf "/opt/node/${NODE_VERSION}/bin/npm" /usr/local/bin/npm && \
    ln -sf "/opt/node/${NODE_VERSION}/bin/npx" /usr/local/bin/npx

RUN curl -fsSL "https://github.com/jdx/mise/releases/download/${MISE_VERSION}/mise-${MISE_VERSION}-linux-x64" \
      -o /usr/local/bin/mise && \
    chmod +x /usr/local/bin/mise

RUN curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" | \
      env UV_UNMANAGED_INSTALL=/usr/local/bin sh

RUN curl -fsSL https://pixi.sh/install.sh | \
      env PIXI_VERSION="${PIXI_VERSION}" PIXI_HOME=/opt/pixi bash && \
    ln -sf /opt/pixi/bin/pixi /usr/local/bin/pixi

RUN ln -sf /usr/bin/fdfind /usr/local/bin/fd

RUN cat >/usr/local/bin/clang-stable <<'EOF' && chmod +x /usr/local/bin/clang-stable
#!/usr/bin/env bash
set -euo pipefail
exec /opt/llvm/current/bin/clang "$@"
EOF

RUN cat >/usr/local/bin/clang-stable++ <<'EOF' && chmod +x /usr/local/bin/clang-stable++
#!/usr/bin/env bash
set -euo pipefail
exec /opt/llvm/current/bin/clang++ "$@"
EOF

RUN locale-gen en_US.UTF-8

ENV LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    VCPKG_ROOT=/opt/vcpkg \
    PATH=/opt/llvm/current/bin:/opt/pixi/bin:/opt/vcpkg:${PATH}

WORKDIR /workspaces

FROM ${CLANG_IMAGE} AS clang_p2996
FROM ${GCC_IMAGE} AS gcc_reflection

FROM ${REPO_BASE_IMAGE} AS final_base

USER root

COPY --from=clang_p2996 /opt/clang-p2996 /opt/clang-p2996
COPY --from=gcc_reflection /opt/gcc-reflection /opt/gcc-reflection

RUN cat >/usr/local/bin/gcc-reflection <<'EOF' && chmod +x /usr/local/bin/gcc-reflection
#!/usr/bin/env bash
set -euo pipefail
exec /opt/gcc-reflection/bin/gcc "$@"
EOF

RUN cat >/usr/local/bin/g++-reflection <<'EOF' && chmod +x /usr/local/bin/g++-reflection
#!/usr/bin/env bash
set -euo pipefail
exec /opt/gcc-reflection/bin/g++ -std=c++26 -freflection "$@"
EOF

RUN cat >/usr/local/bin/clang-p2996 <<'EOF' && chmod +x /usr/local/bin/clang-p2996
#!/usr/bin/env bash
set -euo pipefail
exec /opt/clang-p2996/bin/clang "$@"
EOF

RUN cat >/usr/local/bin/clang-p2996++ <<'EOF' && chmod +x /usr/local/bin/clang-p2996++
#!/usr/bin/env bash
set -euo pipefail
exec /opt/clang-p2996/bin/clang++ -std=c++2c -freflection -freflection-latest -fexpansion-statements -stdlib=libc++ "$@"
EOF

RUN cat >/usr/local/bin/smoke-reflection <<'EOF' && chmod +x /usr/local/bin/smoke-reflection
#!/usr/bin/env bash
set -euo pipefail
cat >/tmp/reflection-smoke.cpp <<'CPP'
#include <meta>
int main() { return 0; }
CPP
/usr/local/bin/g++-reflection /tmp/reflection-smoke.cpp -fsyntax-only
/usr/local/bin/clang-p2996++ /tmp/reflection-smoke.cpp -fsyntax-only
EOF

ENV PATH=/opt/llvm/current/bin:/opt/pixi/bin:/opt/gcc-reflection/bin:/opt/clang-p2996/bin:/opt/vcpkg:${PATH}
WORKDIR /workspaces

RUN smoke-reflection
CMD ["bash"]

FROM ${FINAL_BASE_IMAGE} AS devcontainer

ARG DEVCONTAINER_USERNAME=devcontainer

USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends openssh-client openssh-server && \
    rm -rf /var/lib/apt/lists/*

RUN case "${DEVCONTAINER_USERNAME}" in \
      ""|root) echo "DEVCONTAINER_USERNAME must be a non-root short username" >&2; exit 1 ;; \
      *[!A-Za-z0-9._-]*) echo "DEVCONTAINER_USERNAME contains unsupported characters: ${DEVCONTAINER_USERNAME}" >&2; exit 1 ;; \
    esac && \
    devcontainer_home="/home/${DEVCONTAINER_USERNAME}" && \
    if ! id -u "${DEVCONTAINER_USERNAME}" >/dev/null 2>&1; then \
      existing_group="$(getent group 1000 | cut -d: -f1 || true)"; \
      if getent group "${DEVCONTAINER_USERNAME}" >/dev/null; then \
        group_name="${DEVCONTAINER_USERNAME}"; \
      elif [[ -n "${existing_group}" ]]; then \
        groupmod -n "${DEVCONTAINER_USERNAME}" "${existing_group}"; \
        group_name="${DEVCONTAINER_USERNAME}"; \
      else \
        groupadd --gid 1000 "${DEVCONTAINER_USERNAME}"; \
        group_name="${DEVCONTAINER_USERNAME}"; \
      fi; \
      existing_user="$(getent passwd 1000 | cut -d: -f1 || true)"; \
      if [[ -n "${existing_user}" ]]; then \
        usermod --gid "${group_name}" --login "${DEVCONTAINER_USERNAME}" --home "${devcontainer_home}" --move-home "${existing_user}"; \
      else \
        useradd --uid 1000 --gid "${group_name}" --create-home --home-dir "${devcontainer_home}" --shell /bin/bash "${DEVCONTAINER_USERNAME}"; \
      fi; \
    fi && \
    usermod --append --groups sudo "${DEVCONTAINER_USERNAME}" && \
    echo "${DEVCONTAINER_USERNAME} ALL=(ALL) NOPASSWD:ALL" >"/etc/sudoers.d/${DEVCONTAINER_USERNAME}" && \
    chmod 0440 "/etc/sudoers.d/${DEVCONTAINER_USERNAME}" && \
    chown -R "${DEVCONTAINER_USERNAME}:${DEVCONTAINER_USERNAME}" "${devcontainer_home}" && \
    install -d -o "${DEVCONTAINER_USERNAME}" -g "${DEVCONTAINER_USERNAME}" \
      "${devcontainer_home}/.cache/ccache" \
      "${devcontainer_home}/.cache/mise" \
      "${devcontainer_home}/.cache/sccache" \
      "${devcontainer_home}/.cache/uv" \
      "${devcontainer_home}/.cache/vcpkg" \
      "${devcontainer_home}/.claude" \
      "${devcontainer_home}/.codex" \
      "${devcontainer_home}/.config/gh" \
      "${devcontainer_home}/.gemini" \
      "${devcontainer_home}/.local/bin" \
      "${devcontainer_home}/.local/share/mise" \
      "${devcontainer_home}/.local/state" \
      "${devcontainer_home}/.pixi" \
      "${devcontainer_home}/.ssh"

ENV DEVCONTAINER_USERNAME=${DEVCONTAINER_USERNAME} \
    DEVCONTAINER_HOME=/home/${DEVCONTAINER_USERNAME}

ENV HOME=${DEVCONTAINER_HOME} \
    CCACHE_DIR=${DEVCONTAINER_HOME}/.cache/ccache \
    SCCACHE_DIR=${DEVCONTAINER_HOME}/.cache/sccache \
    VCPKG_DEFAULT_BINARY_CACHE=${DEVCONTAINER_HOME}/.cache/vcpkg \
    VCPKG_BINARY_SOURCES=clear\;files,${DEVCONTAINER_HOME}/.cache/vcpkg,readwrite \
    MISE_DATA_DIR=${DEVCONTAINER_HOME}/.local/share/mise \
    MISE_CACHE_DIR=${DEVCONTAINER_HOME}/.cache/mise \
    MISE_CONFIG_DIR=/workspaces \
    PATH=${DEVCONTAINER_HOME}/.local/bin:${DEVCONTAINER_HOME}/.local/share/mise/shims:${PATH}

USER ${DEVCONTAINER_USERNAME}
WORKDIR /workspaces
