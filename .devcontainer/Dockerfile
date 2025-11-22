# Use Debian trixie as base image for better control over Go installation
FROM debian:trixie

# Make Go version configurable
ARG GO_VERSION=1.25.0

# Build args (may be provided by devcontainer.json)
ARG TZ=Zulu
ARG CLAUDE_CODE_VERSION=latest
ARG GIT_DELTA_VERSION=0.18.2
ARG ZSH_IN_DOCKER_VERSION=1.2.0

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV GOPATH=/go
ENV GOROOT=/usr/local/go
ENV DEVCONTAINER=true

# Create developer user and group
RUN groupadd --gid 1000 developer \
    && useradd --uid 1000 --gid developer --shell /bin/zsh --create-home developer \
    && mkdir -p /etc/sudoers.d \
    && echo developer ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/developer \
    && chmod 0440 /etc/sudoers.d/developer

# Persist bash history
RUN SNIPPET="export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" \
    && mkdir /commandhistory \
    && touch /commandhistory/.bash_history \
    && chown -R developer /commandhistory

# Set timezone if tzdata available (best-effort, no interaction)
RUN if apt-get update >/dev/null 2>&1; then apt-get install -y --no-install-recommends tzdata >/dev/null 2>&1 || true; fi \
    && ln -snf /usr/share/zoneinfo/${TZ} /etc/localtime || true \
    && echo ${TZ} > /etc/timezone || true

RUN apt-get update && apt-get install wget -y \
	&& mkdir -p -m 755 /etc/apt/keyrings \
	&& out=$(mktemp) && wget -nv -O$out https://cli.github.com/packages/githubcli-archive-keyring.gpg \
	&& cat $out | tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
	&& chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
	&& mkdir -p -m 755 /etc/apt/sources.list.d \
	&& echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update

# Install basic packages and dependencies first
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    build-essential \
    ca-certificates \
    gnupg \
    lsb-release \
    sudo \
    vim \
    nano \
    unzip \
    tar \
    tree \
    zsh \
    just \
    gh \
    upx-ucl \
    iptables \
    ipset \
    iproute2 \
    dnsutils \
    jq \
    aggregate \
    less \
    procps \
    fzf \
    man-db \
    python3 \
    python3-pip \
    pipx \
    screen \
    && rm -rf /var/lib/apt/lists/*

# Configure Python and UV
RUN pipx install uv

# Configure Go
RUN wget -O go.tar.gz "https://golang.org/dl/go${GO_VERSION}.linux-amd64.tar.gz" \
    && tar -C /usr/local -xzf go.tar.gz \
    && rm go.tar.gz \
    && chmod +x /usr/local/go/bin/go

## Create Go directories and set proper permissions
RUN mkdir -p /go/pkg/mod && \
    mkdir -p /go/bin && \
    chmod -R 755 /go

## Install buf
ENV BUF_VERSION=1.34.0
RUN curl -sSL -o /usr/local/bin/buf "https://github.com/bufbuild/buf/releases/download/v${BUF_VERSION}/buf-Linux-x86_64" \
    && chmod +x /usr/local/bin/buf

# Configure Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x -o nodesource_setup.sh && \
    bash nodesource_setup.sh && \
    apt-get install -y --no-install-recommends nodejs && \
    rm nodesource_setup.sh

# Install mcp-tasks
RUN npm install -g mcp-tasks
RUN npm install -g chromadb @chroma-core/default-embed

## Ensure default node user has access to /usr/local/share
RUN mkdir -p /usr/local/share/npm-global && \
    chown -R developer:developer /usr/local/share

# Install the firewall script provided by project
# COPY .devcontainer/scripts/init-firewall.sh /usr/local/bin/init-firewall.sh
# RUN chmod +x /usr/local/bin/init-firewall.sh

# Install git-delta as root user
RUN ARCH=$(dpkg --print-architecture) && \
    wget "https://github.com/dandavison/delta/releases/download/${GIT_DELTA_VERSION}/git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb" && \
    dpkg -i "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb" && \
    rm "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb"

RUN mkdir -p /workspace
RUN chown -R developer:developer /home/developer/ /go /workspace

# Switch to developer user
USER developer

RUN pipx ensurepath && pipx completions

# Create Python virtual environment and install OR-Tools using uv
RUN uv venv /home/developer/.venv && \
    uv pip install --python /home/developer/.venv/bin/python ortools

# ============================================================================
# PATH Configuration - Consolidate all PATH settings here
# ============================================================================
ENV VIRTUAL_ENV="/home/developer/.venv"
ENV NPM_CONFIG_PREFIX=/usr/local/share/npm-global

# Set PATH with proper precedence (first = highest priority):
# 1. Python venv binaries
# 2. User local binaries (pipx, uv, etc.)
# 3. Go binaries
# 4. NPM global binaries
# 5. System PATH
ENV PATH="/home/developer/.venv/bin:/home/developer/.local/bin:$GOPATH/bin:$GOROOT/bin:/usr/local/share/npm-global/bin:$PATH"

# Set additional environment variables
ENV SHELL=/bin/zsh
ENV EDITOR=vim
ENV VISUAL=vim

# Configure Git for Go modules and install essential Go tools
RUN git config --global url."https://github.com/".insteadOf "git@github.com:" && \
    git config --global advice.detachedHead false

# Install essential Go tools as developer user
RUN go install golang.org/x/tools/cmd/goimports@latest && \
    go install golang.org/x/tools/gopls@latest && \
    go install github.com/go-delve/delve/cmd/dlv@latest

# Install lefthook for git hooks management
RUN curl -1sLf 'https://dl.cloudsmith.io/public/evilmartians/lefthook/setup.deb.sh' | sudo bash && \
    sudo apt-get update && \
    sudo apt-get install lefthook -y

# Install zsh-in-docker with powerline10k theme
RUN sh -c "$(wget -O- https://github.com/deluan/zsh-in-docker/releases/download/v${ZSH_IN_DOCKER_VERSION}/zsh-in-docker.sh)" -- \
    -p git \
    -p fzf \
    -a "source /usr/share/doc/fzf/examples/key-bindings.zsh" \
    -a "source /usr/share/doc/fzf/examples/completion.zsh" \
    -a "export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" \
    -a "export GOROOT=/usr/local/go" \
    -a "export GOPATH=/go" \
    -a "export VIRTUAL_ENV=/home/developer/.venv" \
    -a "export NPM_CONFIG_PREFIX=/usr/local/share/npm-global" \
    -a "export PATH=\$VIRTUAL_ENV/bin:\$HOME/.local/bin:\$GOPATH/bin:\$GOROOT/bin:\$NPM_CONFIG_PREFIX/bin:\$PATH" \
    -x

# Install Claude Code via npm
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}
RUN npm install -g @google/gemini-cli
ENV IS_SANDBOX=1

# And we need rust.  Claude, unfortunately, has a substantial bug where the terminal goes wild (uncontrolled scrolling) occasionally.  The only workaround documented is https://zellij.dev/.  That isn't supported under debian's package management, so we need other methods to install.  Cargo looks like the easiest, but that requires Rust.
# Documentation: https://github.com/anthropics/claude-code/issues/1495#issuecomment-3236905516
#WORKDIR /tmp
#RUN curl -o rustup-init.sh https://sh.rustup.rs
#RUN chmod +x rustup-init.sh && ./rustup-init.sh -y

#RUN echo '. "$HOME/.cargo/env"' >> ~/.zshrc

# RUN /home/developer/.cargo/bin/cargo install --locked zellij

# Copy and set up firewall script sudoers configuration
#USER root
#RUN chmod +x /usr/local/bin/init-firewall.sh && \
#    echo "developer ALL=(root) NOPASSWD: /usr/local/bin/init-firewall.sh" > /etc/sudoers.d/node-firewall && \
#    chmod 0440 /etc/sudoers.d/node-firewall

# Set working directory
RUN chown developer:developer /workspace
WORKDIR /workspace

# Set default shell
SHELL ["/bin/zsh", "-c"]
