# syntax=docker/dockerfile:1.7

ARG CLANG_BASE_IMAGE=cpp26-dev-clang:dev
ARG GCC_BASE_IMAGE=cpp26-dev-gcc:dev

FROM ${CLANG_BASE_IMAGE} AS clang_p2996
FROM ${GCC_BASE_IMAGE} AS gcc_reflection

FROM clang_p2996 AS runtime

ARG DEBIAN_FRONTEND=noninteractive
ARG NODE_VERSION=25.8.1
ARG NODE_MAJOR=25
ARG MISE_VERSION=v2026.3.10
ARG UV_VERSION=0.10.12
ARG PIXI_VERSION=v0.66.0
ARG LLVM_VERSION=22.1.1
ARG LLVM_ARCHIVE=LLVM-22.1.1-Linux-X64.tar.xz
ARG LLVM_DOWNLOAD_URL=https://github.com/llvm/llvm-project/releases/download/llvmorg-22.1.1/LLVM-22.1.1-Linux-X64.tar.xz

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
      ca-certificates \
      cppcheck \
      curl \
      docker-buildx-plugin \
      docker-ce-cli \
      fd-find \
      git \
      git-lfs \
      graphviz \
      jq \
      lcov \
      linux-tools-generic \
      locales \
      mold \
      pkg-config \
      ripgrep \
      rsync \
      shellcheck \
      sudo \
      time \
      xz-utils && \
    rm -rf /var/lib/apt/lists/*

COPY --from=gcc_reflection /opt/gcc-reflection /opt/gcc-reflection

RUN if [[ -e /usr/local/bin/clang++ ]]; then \
      mv /usr/local/bin/clang++ /usr/local/bin/clang-p2996++-real; \
    fi && \
    rm -f /usr/local/bin/clang && \
    ln -sf /usr/local/bin/clang-p2996++-real /usr/local/bin/clang-p2996-real

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

RUN if ! id -u vscode >/dev/null 2>&1; then \
      existing_group="$(getent group 1000 | cut -d: -f1 || true)"; \
      if getent group vscode >/dev/null; then \
        group_name=vscode; \
      elif [[ -n "${existing_group}" ]]; then \
        groupmod -n vscode "${existing_group}"; \
        group_name=vscode; \
      else \
        groupadd --gid 1000 vscode; \
        group_name=vscode; \
      fi; \
      existing_user="$(getent passwd 1000 | cut -d: -f1 || true)"; \
      if [[ -n "${existing_user}" ]]; then \
        usermod --gid "${group_name}" --login vscode --home /home/vscode --move-home "${existing_user}"; \
      else \
        useradd --uid 1000 --gid "${group_name}" --create-home --shell /bin/bash vscode; \
      fi; \
    fi && \
    usermod --append --groups sudo vscode && \
    echo "vscode ALL=(ALL) NOPASSWD:ALL" >/etc/sudoers.d/vscode && \
    chmod 0440 /etc/sudoers.d/vscode && \
    chown -R vscode:vscode /home/vscode && \
    install -d -o vscode -g vscode \
      /home/vscode/.cache/ccache \
      /home/vscode/.cache/sccache \
      /home/vscode/.cache/uv \
      /home/vscode/.cache/vcpkg \
      /home/vscode/.codex \
      /home/vscode/.claude \
      /home/vscode/.gemini \
      /home/vscode/.local/bin \
      /home/vscode/.local/share/mise \
      /home/vscode/.pixi

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
exec /usr/local/bin/clang-p2996-real "$@"
EOF

RUN cat >/usr/local/bin/clang-p2996++ <<'EOF' && chmod +x /usr/local/bin/clang-p2996++
#!/usr/bin/env bash
set -euo pipefail
exec /usr/local/bin/clang-p2996++-real -std=c++2c -freflection -freflection-latest -fexpansion-statements -stdlib=libc++ "$@"
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

RUN locale-gen en_US.UTF-8

ENV LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    CCACHE_DIR=/home/vscode/.cache/ccache \
    SCCACHE_DIR=/home/vscode/.cache/sccache \
    VCPKG_DEFAULT_BINARY_CACHE=/home/vscode/.cache/vcpkg \
    VCPKG_BINARY_SOURCES=clear\;files,/home/vscode/.cache/vcpkg,readwrite \
    MISE_DATA_DIR=/home/vscode/.local/share/mise \
    MISE_CACHE_DIR=/home/vscode/.cache/mise \
    MISE_CONFIG_DIR=/workspaces \
    PATH=/opt/llvm/current/bin:/home/vscode/.local/bin:/home/vscode/.local/share/mise/shims:/opt/pixi/bin:/opt/gcc-reflection/bin:/opt/vcpkg:${PATH}

USER vscode
WORKDIR /workspaces

RUN smoke-reflection
