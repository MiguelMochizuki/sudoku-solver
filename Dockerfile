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

# SWI-Prolog home without the packages this app never loads. Only ext/clib
# (library(time) for call_with_time_limit) and ext/swipy are kept.
FROM base AS swipl-slim
RUN cd /usr/lib/swi-prolog/library/ext && ls | grep -vxE 'clib|swipy' | xargs rm -rf \
 && cd /usr/lib/swi-prolog/lib/*-linux \
 && rm -f archive4pl.so double_metaphone.so http_stream.so inclpr.so isub.so json.so \
      libedit4pl.so ntriples.so pcre4pl.so pdt_console.so porter_stem.so protobufs.so \
      rdf_db.so readline4pl.so redis4pl.so sgml2pl.so snowball.so ssl4pl.so crypto4pl.so \
      sweep-module.so table.so test_cpp.so test_ffi.so
# libswipl and libgmp live in an arch-specific dir (x86_64-linux-gnu, aarch64-linux-gnu);
# stage them in a neutral one so the runtime stage is the same on every platform.
RUN mkdir /swipl-libs && cp -P /usr/lib/*-linux-gnu/libswipl.so.9* /usr/lib/*-linux-gnu/libgmp.so.10* /swipl-libs/

# Production (default target, must stay last): distroless Python, no shell or apt.
# SWI-Prolog is not packaged for distroless, so its runtime is copied from the
# swipl-slim stage; libswipl only needs libgmp beyond what distroless already ships.
FROM gcr.io/distroless/python3-debian13 AS runtime
COPY --from=swipl-slim /usr/lib/swi-prolog /usr/lib/swi-prolog
COPY --from=swipl-slim /swipl-libs /opt/swipl-libs
COPY --from=prod-venv /opt/venv/lib/python3.13/site-packages /opt/site-packages
ENV PYTHONPATH=/opt/site-packages LD_LIBRARY_PATH=/opt/swipl-libs
WORKDIR /app
COPY src ./src
USER nonroot
EXPOSE 8501
ENTRYPOINT ["/usr/bin/python3", "-m", "uvicorn"]
CMD ["src.main:app", "--host", "0.0.0.0", "--port", "8501"]
