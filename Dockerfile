#
# Spiderfoot Dockerfile - Enterprise Edition
# Improved version with virtual environment support and FastAPI
#

# ── Stage: Compile Go recon tools ───────────────────────────────────────────
# Binaries for the modules ported from upstream poppopjmp/spiderfoot
# (sfp_httpx, sfp_subfinder, sfp_tool_dnsx, sfp_tool_naabu, sfp_tool_katana,
# sfp_tool_tlsx, sfp_tool_ffuf, sfp_tool_amass, sfp_tool_gau,
# sfp_tool_waybackurls, sfp_tool_gospider, sfp_tool_hakrawler,
# sfp_tool_gowitness, sfp_tool_gitleaks, sfp_tool_dalfox). Recipe matches
# upstream's own docker/Dockerfile.active-scanner.
FROM golang:1.24-bookworm AS go-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpcap-dev git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV GOBIN=/tools/bin GOTOOLCHAIN=auto
RUN mkdir -p /tools/bin

# ProjectDiscovery suite
RUN go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
RUN go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
RUN go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest
RUN go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest
RUN go install -v github.com/projectdiscovery/katana/cmd/katana@latest
RUN go install -v github.com/projectdiscovery/tlsx/cmd/tlsx@latest

# Brute-forcing / fuzzing
RUN go install -v github.com/ffuf/ffuf/v2@latest

# Attack surface mapping
RUN go install -v github.com/owasp-amass/amass/v4/...@master

# URL discovery
RUN go install -v github.com/lc/gau/v2/cmd/gau@latest
RUN go install -v github.com/tomnomnom/waybackurls@latest

# Web crawling
RUN go install -v github.com/jaeles-project/gospider@latest
RUN go install -v github.com/hakluke/hakrawler@latest

# Screenshotting
RUN go install -v github.com/sensepost/gowitness@latest

# Secret detection
RUN go install -v github.com/zricethezav/gitleaks/v8@latest

# XSS scanning
RUN go install -v github.com/hahwul/dalfox/v2@latest


# ── Stage: Compile C recon tools ────────────────────────────────────────────
# Binaries for sfp_tool_massdns, sfp_tool_masscan.
FROM debian:bookworm-slim AS c-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    git make gcc libc6-dev libpcap-dev ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /tools/bin

# massdns
RUN git clone --depth 1 https://github.com/blechschmidt/massdns.git /build/massdns && \
    cd /build/massdns && make && cp bin/massdns /tools/bin/massdns

# masscan
RUN git clone --depth 1 https://github.com/robertdavidgraham/masscan.git /build/masscan && \
    cd /build/masscan && make -j$(nproc) && cp bin/masscan /tools/bin/masscan


# Build stage
FROM python:3.11-slim-bookworm AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    libxml2-dev \
    libxslt-dev \
    libjpeg-dev \
    zlib1g-dev \
    libffi-dev \
    libssl-dev \
    python3-dev \
    git \
    curl \
    wget \
    unzip \
    npm \
    swig \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python packages
ARG REQUIREMENTS=requirements.txt
COPY $REQUIREMENTS requirements.txt ./

# Install Python packages in virtual environment
RUN pip install --no-cache-dir -U pip==25.0.1 && \
    pip install --no-cache-dir -r requirements.txt && \
    # Install additional security tools
    pip install --no-cache-dir dnstwist snallygaster trufflehog wafw00f && \
    # Tools needed by modules ported from upstream poppopjmp/spiderfoot:
    # sfp_tool_arjun, sfp_tool_sslyze. (sfp_tool_linkfinder is handled
    # separately below — no PyPI package named "linkfinder" actually
    # exists, despite the module's own docstring claiming
    # `pip install linkfinder`; verified against PyPI and the real
    # GerbenJavado/LinkFinder setup.py, which defines no console script.)
    pip install --no-cache-dir \
        arjun \
        sslyze

# Download and build tools
RUN mkdir -p /tools/bin && \
    # Nuclei
    wget -q https://github.com/projectdiscovery/nuclei/releases/download/v3.3.9/nuclei_3.3.9_linux_amd64.zip && \
    unzip nuclei_3.3.9_linux_amd64.zip -d /tools/bin && \
    rm nuclei_3.3.9_linux_amd64.zip && \
    chmod +x /tools/bin/nuclei && \
    # Nuclei templates
    git clone --depth 1 https://github.com/projectdiscovery/nuclei-templates.git /tools/nuclei-templates && \
    # Node.js tools
    npm config set prefix /tools && \
    npm install -g retire && \
    # Git tools
    git clone --depth 1 https://github.com/testssl/testssl.sh.git /tools/testssl.sh && \
    git clone --depth 1 https://github.com/Tuhinshubhra/CMSeeK /tools/CMSeeK && \
    pip install --no-cache-dir -r /tools/CMSeeK/requirements.txt && \
    mkdir /tools/CMSeeK/Results && \
    # Nikto — needed by sfp_tool_nikto. It's a Perl script, not a compiled
    # binary; runtime stage symlinks nikto.pl onto PATH as `nikto`.
    git clone --depth 1 https://github.com/sullo/nikto.git /tools/nikto && \
    rm -rf /tools/nikto/.git && \
    # LinkFinder — needed by sfp_tool_linkfinder. Also a Python script, not
    # a PyPI package (see note above). The module itself knows how to
    # invoke a .py path directly (python3 <path>), so no wrapper/symlink
    # is needed — just set SF__SFP_TOOL_LINKFINDER__LINKFINDER_PATH to
    # this exact path in the compose env.
    git clone --depth 1 https://github.com/GerbenJavado/LinkFinder.git /tools/LinkFinder && \
    rm -rf /tools/LinkFinder/.git && \
    pip install --no-cache-dir -r /tools/LinkFinder/requirements.txt

# Runtime stage
FROM python:3.11-slim-bookworm

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 \
    libxslt1.1 \
    libjpeg62-turbo \
    zlib1g \
    nbtscan \
    onesixtyone \
    nmap \
    whatweb \
    bsdmainutils \
    dnsutils \
    coreutils \
    libcap2-bin \
    ca-certificates \
    # sfp_tool_sslscan
    sslscan \
    # nikto is Perl — its deps
    perl libnet-ssleay-perl libwhisker2-perl libjson-perl libxml-writer-perl \
    # naabu/massdns/masscan raw-packet libs
    libpcap0.8 \
    # sfp_tool_gowitness (chrome_path option)
    chromium \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Remove SQLite3 to force PostgreSQL-only usage
RUN rm -rf /usr/local/lib/python3.11/sqlite3 \
    /usr/local/lib/python3.11/lib-dynload/_sqlite3*.so \
    /usr/lib/python3.*/sqlite3 \
    /usr/lib/python3.*/lib-dynload/_sqlite3*.so 2>/dev/null || true

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy tools from builder (nuclei, testssl.sh, CMSeeK, nikto, retire)
COPY --from=builder /tools /tools

# Copy tools compiled in the go-builder / c-builder stages
COPY --from=go-builder /tools/bin/ /tools/bin/
COPY --from=c-builder  /tools/bin/ /tools/bin/

# Nikto is a Perl script, not a binary — symlink it onto PATH as `nikto`
RUN ln -sf /tools/nikto/program/nikto.pl /usr/local/bin/nikto && \
    chmod +x /tools/nikto/program/nikto.pl

# Create user and directories
RUN addgroup --system spiderfoot && \
    adduser --system --ingroup spiderfoot --home /home/spiderfoot \
            --shell /usr/sbin/nologin --gecos "SpiderFoot User" spiderfoot && \
    mkdir -p /home/spiderfoot/data /home/spiderfoot/logs /home/spiderfoot/cache /home/spiderfoot/.spiderfoot/logs && \
    # Do NOT chown bind-mounted folders here; this causes errors if the host directory is mounted at runtime.
    # Only set ownership for files inside the image.
    chown -R spiderfoot:spiderfoot /home/spiderfoot


# Set up environment with virtual environment
ENV SPIDERFOOT_DATA=/home/spiderfoot/data \
    SPIDERFOOT_LOGS=/home/spiderfoot/logs \
    SPIDERFOOT_CACHE=/home/spiderfoot/cache \
    PATH="/opt/venv/bin:/tools/bin:$PATH" \
    PYTHONPATH="/home/spiderfoot:/home/spiderfoot/modules" \
    VIRTUAL_ENV="/opt/venv"


# Enable raw-socket capabilities for network scanners
RUN setcap cap_net_raw,cap_net_admin=eip /usr/bin/nmap && \
    setcap cap_net_raw,cap_net_admin=eip /tools/bin/naabu    2>/dev/null || true && \
    setcap cap_net_raw,cap_net_admin=eip /tools/bin/massdns  2>/dev/null || true && \
    setcap cap_net_raw,cap_net_admin=eip /tools/bin/masscan  2>/dev/null || true

# Make all downloaded/compiled tools executable
RUN chmod +x /tools/bin/*

# Copy application files (excluding database)
WORKDIR /home/spiderfoot

# Copy the rest of the application files
COPY --chown=spiderfoot:spiderfoot . .

# Inject build metadata
ARG BUILD_DATE
ARG BUILD_COMMIT
RUN echo "${BUILD_DATE}-${BUILD_COMMIT}" > /home/spiderfoot/BUILD_INFO && \
    chown spiderfoot:spiderfoot /home/spiderfoot/BUILD_INFO

# Copy and set up the startup script
COPY --chown=root:root docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Remove any database files from application directory to prevent conflicts
RUN rm -f /home/spiderfoot/spiderfoot.db && \
    # Do NOT chown bind-mounted folders (e.g., /home/spiderfoot/data, /home/spiderfoot/logs, /home/spiderfoot/cache, /etc/spiderfoot) here; this causes errors if the host directory is mounted at runtime.
    # Only set ownership for files and folders created inside the image, not for host bind-mounts.
    rm -f /home/spiderfoot/data/spiderfoot.db

# Remove any existing logs that might have been copied and recreate logs directory
RUN rm -rf /home/spiderfoot/logs && \
    mkdir -p /home/spiderfoot/logs && \
    chown -R spiderfoot:spiderfoot /home/spiderfoot/logs && \
    chmod -R 755 /home/spiderfoot/logs

# Ensure the correct database directory structure exists
RUN mkdir -p /home/spiderfoot/.spiderfoot && \
    chown -R spiderfoot:spiderfoot /home/spiderfoot/.spiderfoot

# Create __init__.py files if they don't exist
RUN touch /home/spiderfoot/__init__.py && \
    touch /home/spiderfoot/modules/__init__.py && \
    touch /home/spiderfoot/spiderfoot/__init__.py

# Ensure proper ownership of all application files and directories (final step)
RUN chown -R spiderfoot:spiderfoot /home/spiderfoot 

USER spiderfoot

# Expose ports for both web UI and API
EXPOSE 5001 8001

# Default command with support for both web UI and API
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh", "python"]
CMD ["sf.py", "--both", "-l", "0.0.0.0:5001", "--api-listen", "0.0.0.0:8001"]

# ---
# NOTE: For persistent storage, logs, cache, and config, ensure the following paths are writeable by the spiderfoot user inside the container:
#   - /home/spiderfoot/data           (main data, including spiderfoot.db)
#   - /home/spiderfoot/cache          (cache)
#   - /home/spiderfoot/logs           (logs)
#   - /home/spiderfoot/config         (config, if used)
# If these are bind-mounted from the host, you must set correct permissions/ownership on the host before starting the container.
# The Dockerfile cannot change ownership of bind-mounted folders at runtime.
# ---
