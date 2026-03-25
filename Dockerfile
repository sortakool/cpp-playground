# syntax=docker/dockerfile:1.7

ARG BASE_DISTRO=ubuntu
ARG BASE_VERSION=25.10

FROM ${BASE_DISTRO}:${BASE_VERSION} AS base

ARG DEBIAN_FRONTEND=noninteractive
ARG APT_SNAPSHOT=20260322T000000Z
ARG MISE_VERSION=2026.3.10
ARG LLVM_VERSION=22.1.1
ARG LLVM_ARCHIVE=LLVM-${LLVM_VERSION}-Linux-X64.tar.xz
ARG LLVM_DOWNLOAD_URL=https://github.com/llvm/llvm-project/releases/download/llvmorg-${LLVM_VERSION}/${LLVM_ARCHIVE}

ENV DEBIAN_FRONTEND=${DEBIAN_FRONTEND} \
    CPP_PLAYGROUND_REPO_ROOT=/opt/cpp-playground \
    MISE_CACHE_DIR=/var/cache/mise \
    MISE_DATA_DIR=/opt/mise \
    MISE_IGNORED_CONFIG_PATHS=/root/.config/mise \
    PATH=/opt/mise/shims:/root/.local/bin:${PATH}

WORKDIR /opt/cpp-playground

RUN distro="$(. /etc/os-release && printf '%s' "$ID")" && \
    codename="$(. /etc/os-release && printf '%s' "$VERSION_CODENAME")" && \
    case "$distro" in \
      ubuntu) \
        apt-get update && \
        apt-get install -y --no-install-recommends ca-certificates ubuntu-keyring && \
        find /etc/apt/sources.list.d -name '*.sources' -exec \
          sed -i -E "s|URIs: https?://[^ ]+/ubuntu/?|URIs: https://snapshot.ubuntu.com/ubuntu/${APT_SNAPSHOT}/|g" {} + && \
        printf 'Acquire::Check-Valid-Until "false";\n' >/etc/apt/apt.conf.d/90cpp-playground-snapshot && \
        rm -rf /var/lib/apt/lists/* \
        ;; \
      debian) \
        printf '%s\n' \
          'Types: deb' \
          "URIs: http://snapshot.debian.org/archive/debian/${APT_SNAPSHOT}/" \
          "Suites: ${codename} ${codename}-updates" \
          'Components: main' \
          'Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg' \
          '' \
          'Types: deb' \
          "URIs: http://snapshot.debian.org/archive/debian-security/${APT_SNAPSHOT}/" \
          "Suites: ${codename}-security" \
          'Components: main' \
          'Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg' \
          >/etc/apt/sources.list.d/debian.sources && \
        printf 'Acquire::Check-Valid-Until "false";\n' >/etc/apt/apt.conf.d/90cpp-playground-snapshot \
        ;; \
      *) \
        echo "unsupported base distro: $distro" >&2 && \
        exit 1 \
        ;; \
    esac && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      bash-completion \
      bear \
      build-essential \
      ccache \
      cmake \
      cppcheck \
      curl \
      fd-find \
      gdb \
      git \
      git-lfs \
      graphviz \
      jq \
      lcov \
      libssl-dev \
      lldb \
      locales \
      make \
      mold \
      ninja-build \
      pkg-config \
      python3 \
      python3-pip \
      python3-venv \
      ripgrep \
      rsync \
      shellcheck \
      time \
      unzip \
      valgrind \
      wget \
      xz-utils \
      zip \
      zlib1g-dev && \
    ln -sf /usr/bin/fdfind /usr/local/bin/fd && \
    locale-gen en_US.UTF-8 && \
    rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "${LLVM_DOWNLOAD_URL}" -o "/tmp/${LLVM_ARCHIVE}" && \
    mkdir -p /opt/llvm && \
    tar -C /opt -xf "/tmp/${LLVM_ARCHIVE}" && \
    mv "/opt/${LLVM_ARCHIVE%.tar.xz}" "/opt/llvm/${LLVM_VERSION}" && \
    ln -sfn "/opt/llvm/${LLVM_VERSION}" /opt/llvm/current && \
    rm -f "/tmp/${LLVM_ARCHIVE}"

ENV LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    LLVM_HOME=/opt/llvm/current \
    PATH=/opt/llvm/current/bin:/opt/mise/shims:/root/.local/bin:${PATH}

FROM base AS clang

ARG DEBIAN_FRONTEND=noninteractive
ARG CLANG_P2996_REPO=https://github.com/bloomberg/clang-p2996.git
ARG CLANG_P2996_REF=a5270822dede40aaaf2c62381b89f110d2cfda4c

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libedit-dev \
      libffi-dev \
      libncurses5-dev \
      libxml2-dev \
      libzstd-dev \
      swig && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt/clang-p2996

RUN git init . && \
    git remote add origin "${CLANG_P2996_REPO}" && \
    git fetch --depth 1 origin "${CLANG_P2996_REF}" && \
    git checkout FETCH_HEAD

WORKDIR /opt/clang-p2996/build

RUN cmake -G Ninja ../llvm \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX=/opt/clang-p2996 \
      -DCMAKE_C_COMPILER=gcc \
      -DCMAKE_CXX_COMPILER=g++ \
      -DLLVM_ENABLE_PROJECTS=clang\;lld \
      -DLLVM_ENABLE_RUNTIMES=libcxx\;libcxxabi\;libunwind \
      -DLLVM_TARGETS_TO_BUILD=X86 \
      -DLLVM_CCACHE_BUILD=ON \
      -DLLVM_ENABLE_BINDINGS=OFF \
      -DLLVM_ENABLE_TERMINFO=OFF \
      -DLLVM_INCLUDE_BENCHMARKS=OFF \
      -DLLVM_INCLUDE_EXAMPLES=OFF \
      -DLLVM_INCLUDE_TESTS=OFF \
      -DCLANG_DEFAULT_CXX_STDLIB=libc++ && \
    ninja install

RUN printf '#include <meta>\nint main(){return 0;}\n' >/tmp/refl.cpp && \
    /opt/clang-p2996/bin/clang++ \
      -std=c++2c \
      -freflection \
      -freflection-latest \
      -fexpansion-statements \
      -stdlib=libc++ \
      /tmp/refl.cpp \
      -fsyntax-only && \
    rm -f /tmp/refl.cpp

FROM base AS gcc

ARG DEBIAN_FRONTEND=noninteractive
ARG GCC_REFLECTION_REPO=https://forge.sourceware.org/marek/gcc.git
ARG GCC_REFLECTION_REF=95f5ec013f4ce8b3cd7f6f4434d3c36db11526a8

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      bison \
      flex \
      gawk \
      libgmp-dev \
      libisl-dev \
      libmpc-dev \
      libmpfr-dev \
      texinfo && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt/gcc-reflection

RUN git init . && \
    git remote add origin "${GCC_REFLECTION_REPO}" && \
    git fetch --depth 1 origin "${GCC_REFLECTION_REF}" && \
    git checkout FETCH_HEAD

WORKDIR /opt/gcc-reflection/build

RUN ../configure \
      --prefix=/opt/gcc-reflection \
      --enable-languages=c,c++ \
      --disable-bootstrap \
      --disable-multilib && \
    make -j"$(nproc)" && \
    make install

RUN printf '#include <meta>\nint main(){return 0;}\n' >/tmp/refl.cpp && \
    /opt/gcc-reflection/bin/g++ \
      -std=c++26 \
      -freflection \
      /tmp/refl.cpp \
      -fsyntax-only && \
    rm -f /tmp/refl.cpp

FROM base AS final

COPY --from=clang /opt/clang-p2996 /opt/clang-p2996
COPY --from=gcc /opt/gcc-reflection /opt/gcc-reflection

ENV PATH=/opt/clang-p2996/bin:/opt/gcc-reflection/bin:/opt/llvm/current/bin:/opt/mise/shims:/root/.local/bin:${PATH}

RUN printf '#include <meta>\nint main(){return 0;}\n' >/tmp/reflection-smoke.cpp && \
    /opt/gcc-reflection/bin/g++ \
      -std=c++26 \
      -freflection \
      /tmp/reflection-smoke.cpp \
      -fsyntax-only && \
    /opt/clang-p2996/bin/clang++ \
      -std=c++2c \
      -freflection \
      -freflection-latest \
      -fexpansion-statements \
      -stdlib=libc++ \
      /tmp/reflection-smoke.cpp \
      -fsyntax-only && \
    rm -f /tmp/reflection-smoke.cpp

COPY .chezmoiversion /opt/cpp-playground/.chezmoiversion
COPY docker-bake.hcl /opt/cpp-playground/docker-bake.hcl
COPY hk.pkl /opt/cpp-playground/hk.pkl
COPY install.sh /opt/cpp-playground/install.sh
COPY mise.lock /opt/cpp-playground/mise.lock
COPY mise.toml /opt/cpp-playground/mise.toml
COPY pixi.toml /opt/cpp-playground/pixi.toml
COPY pixi.lock /opt/cpp-playground/pixi.lock
COPY pyproject.toml /opt/cpp-playground/pyproject.toml
COPY uv.lock /opt/cpp-playground/uv.lock
COPY home /opt/cpp-playground/home
COPY src/cpp_playground /opt/cpp-playground/src/cpp_playground

RUN chmod +x /opt/cpp-playground/install.sh && \
    /opt/cpp-playground/install.sh

COPY . /opt/cpp-playground

WORKDIR /workspaces

FROM final AS devcontainer

ARG DEBIAN_FRONTEND=noninteractive
ARG DEVCONTAINER_USERNAME=devcontainer

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      openssh-client \
      openssh-server \
      sudo && \
    rm -rf /var/lib/apt/lists/*

RUN case "${DEVCONTAINER_USERNAME}" in \
      ""|root) \
        echo "DEVCONTAINER_USERNAME must be a non-root short username" >&2 && \
        exit 1 \
        ;; \
      *[!A-Za-z0-9._-]*) \
        echo "DEVCONTAINER_USERNAME contains unsupported characters: ${DEVCONTAINER_USERNAME}" >&2 && \
        exit 1 \
        ;; \
    esac && \
    devcontainer_home="/home/${DEVCONTAINER_USERNAME}" && \
    if ! id -u "${DEVCONTAINER_USERNAME}" >/dev/null 2>&1; then \
      existing_group="$(getent group 1000 || true)"; \
      existing_group="${existing_group%%:*}"; \
      if getent group "${DEVCONTAINER_USERNAME}" >/dev/null 2>&1; then \
        group_name="${DEVCONTAINER_USERNAME}"; \
      elif [ -n "${existing_group}" ]; then \
        groupmod -n "${DEVCONTAINER_USERNAME}" "${existing_group}"; \
        group_name="${DEVCONTAINER_USERNAME}"; \
      else \
        groupadd --gid 1000 "${DEVCONTAINER_USERNAME}"; \
        group_name="${DEVCONTAINER_USERNAME}"; \
      fi; \
      existing_user="$(getent passwd 1000 || true)"; \
      existing_user="${existing_user%%:*}"; \
      if [ -n "${existing_user}" ]; then \
        usermod --gid "${group_name}" --login "${DEVCONTAINER_USERNAME}" --home "${devcontainer_home}" --move-home "${existing_user}"; \
      else \
        useradd --uid 1000 --gid "${group_name}" --create-home --home-dir "${devcontainer_home}" --shell /bin/sh "${DEVCONTAINER_USERNAME}"; \
      fi; \
    fi && \
    usermod --append --groups sudo "${DEVCONTAINER_USERNAME}" && \
    printf '%s ALL=(ALL) NOPASSWD:ALL\n' "${DEVCONTAINER_USERNAME}" >"/etc/sudoers.d/${DEVCONTAINER_USERNAME}" && \
    chmod 0440 "/etc/sudoers.d/${DEVCONTAINER_USERNAME}" && \
    chown -R "${DEVCONTAINER_USERNAME}:${DEVCONTAINER_USERNAME}" "${devcontainer_home}" && \
    install -d -o "${DEVCONTAINER_USERNAME}" -g "${DEVCONTAINER_USERNAME}" \
      "${devcontainer_home}/.cache/ccache" \
      "${devcontainer_home}/.cache/mise" \
      "${devcontainer_home}/.cache/uv" \
      "${devcontainer_home}/.config/gh" \
      "${devcontainer_home}/.local/bin" \
      "${devcontainer_home}/.local/share/mise" \
      "${devcontainer_home}/.local/state" \
      "${devcontainer_home}/.pixi" \
      "${devcontainer_home}/.ssh"

ENV DEVCONTAINER_USERNAME=${DEVCONTAINER_USERNAME} \
    DEVCONTAINER_HOME=/home/${DEVCONTAINER_USERNAME} \
    HOME=/home/${DEVCONTAINER_USERNAME} \
    CCACHE_DIR=/home/${DEVCONTAINER_USERNAME}/.cache/ccache \
    MISE_CACHE_DIR=/home/${DEVCONTAINER_USERNAME}/.cache/mise \
    PATH=/home/${DEVCONTAINER_USERNAME}/.local/bin:/opt/clang-p2996/bin:/opt/gcc-reflection/bin:/opt/llvm/current/bin:/opt/mise/shims:${PATH}

USER ${DEVCONTAINER_USERNAME}
WORKDIR /workspaces
