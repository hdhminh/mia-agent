FROM pgvector/pgvector:pg17

ARG PG_TEXTSEARCH_VERSION=1.3.1
ARG TARGETARCH

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl unzip; \
    case "${TARGETARCH:-}" in \
      arm64) pkg_arch="arm64" ;; \
      amd64) pkg_arch="amd64" ;; \
      *) pkg_arch="$(dpkg --print-architecture)" ;; \
    esac; \
    curl -fsSL \
      "https://github.com/timescale/pg_textsearch/releases/download/v${PG_TEXTSEARCH_VERSION}/pg-textsearch-v${PG_TEXTSEARCH_VERSION}-pg17-${pkg_arch}.zip" \
      -o /tmp/pg_textsearch.zip; \
    unzip /tmp/pg_textsearch.zip -d /tmp/pg_textsearch; \
    apt-get install -y --no-install-recommends /tmp/pg_textsearch/*.deb; \
    rm -rf /var/lib/apt/lists/* /tmp/pg_textsearch /tmp/pg_textsearch.zip
