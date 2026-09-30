FROM debian:trixie-slim AS builder

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      swi-prolog-nox python3 python3-venv python3-dev build-essential pkg-config \
 && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Dev venv: runtime deps + test/reload extras (pip kept).
FROM builder AS dev-venv
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements-dev.txt

# Prod venv: runtime deps only, pip removed.
FROM builder AS prod-venv
RUN /opt/venv/bin/pip uninstall -y pip

# Shared runtime base: interpreters only, no build toolchain.
FROM debian:trixie-slim AS base

RUN apt-get update \
 && apt-get install -y --no-install-recommends swi-prolog-nox python3 \
 && rm -rf /var/lib/apt/lists/* \
      /usr/lib/swi-prolog/test /usr/lib/swi-prolog/demo /usr/lib/swi-prolog/include /usr/lib/swi-prolog/cmake \
      /usr/lib/python3.13/test /usr/lib/python3.13/idlelib /usr/lib/python3.13/tkinter \
      /usr/lib/python3.13/turtledemo /usr/lib/python3.13/ensurepip \
      /usr/share/doc /usr/share/man

WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH"
RUN useradd -m appuser

# Development: source is bind-mounted by docker-compose.yml.
FROM base AS dev
COPY --from=dev-venv /opt/venv /opt/venv
USER appuser
EXPOSE 8501
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8501", "--reload", "--reload-dir", "src"]

# Production (default target, must stay last).
FROM base AS runtime
COPY --from=prod-venv /opt/venv /opt/venv
COPY . .
USER appuser
EXPOSE 8501
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8501"]
