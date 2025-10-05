# -------- Base image --------
FROM python:3.12.6-slim

# -------- OS deps (wget/unzip) + common Chrome runtime libs --------
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget unzip ca-certificates gnupg \
    libasound2 libatk-bridge2.0-0 libgbm1 libgtk-3-0 libnss3 libx11-6 \
    libx11-xcb1 libxcomposite1 libxcursor1 libxdamage1 libxi6 libxrandr2 \
    libxrender1 xdg-utils fonts-liberation \
 && rm -rf /var/lib/apt/lists/*

# -------- Get Chrome for Testing + matching chromedriver --------
WORKDIR /data
ARG CHROME_VERSION=136.0.7103.113

RUN if [ ! -e chrome-linux64 ]; then \
      wget -q https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chrome-linux64.zip && \
      unzip -q chrome-linux64.zip && rm chrome-linux64.zip ; \
    fi && \
    if [ ! -e chromedriver-linux64 ]; then \
      wget -q https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip && \
      unzip -q chromedriver-linux64.zip && rm chromedriver-linux64.zip ; \
    fi

# Expose Chrome + Chromedriver on PATH
ENV CHROME_BIN=/data/chrome-linux64/chrome \
    CHROMEDRIVER=/data/chromedriver-linux64/chromedriver \
    PATH="/data/chrome-linux64:/data/chromedriver-linux64:${PATH}"

RUN chmod +x /data/chromedriver-linux64/chromedriver


# -------- Install uv (Astral) --------

# Set the working directory in the container
WORKDIR /app

# Install uv by copying the binary from the official distroless Docker image
COPY --from=ghcr.io/astral-sh/uv:0.6.6 /uv /uvx /bin/

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy the current directory contents into the container at /app
COPY . /app

# Installing the project separately from its dependencies allows optimal layer caching
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# After setting CHROME_BIN and CHROMEDRIVER
RUN "$CHROME_BIN" --version && "$CHROMEDRIVER" --version


# -------- Run Script --------
CMD ["uv", "run", "main.py"]
