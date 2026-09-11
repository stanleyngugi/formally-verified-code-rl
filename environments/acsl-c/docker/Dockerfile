FROM ubuntu:24.04 AS build

ARG DEBIAN_FRONTEND=noninteractive
ARG OCAML_VERSION=4.14.2
ARG FRAMAC_VERSION=33.0
ARG WHY3_VERSION=1.8.2
ARG ALT_ERGO_VERSION=2.6.3
ARG OPAM_UID=10001

RUN apt-get update && apt-get install -y --no-install-recommends \
    bubblewrap build-essential ca-certificates git graphviz libgmp-dev m4 opam \
    pkg-config rsync unzip zlib1g-dev && \
    rm -rf /var/lib/apt/lists/* && \
    useradd --create-home --uid "${OPAM_UID}" opam

USER opam
ENV OPAMROOT=/home/opam/.opam
# opam's wget default can wait forever on a stalled TCP transfer. Bound each
# network read while retaining opam's own retry count and checksum validation.
ENV OPAMFETCH="wget --content-disposition --timeout=30 --read-timeout=30 --tries=%{retry}% -O %{out}% -- %{url}%"
RUN opam init --disable-sandboxing --bare --yes && \
    opam switch create verified "ocaml-base-compiler.${OCAML_VERSION}" --yes && \
    opam install --switch verified --yes \
      "frama-c.${FRAMAC_VERSION}" \
      "why3.${WHY3_VERSION}" \
      "alt-ergo.${ALT_ERGO_VERSION}"
RUN rm -rf \
      "${OPAMROOT}/download-cache" \
      "${OPAMROOT}/log" \
      "${OPAMROOT}/repo" \
      "${OPAMROOT}/verified/.opam-switch/build" \
      "${OPAMROOT}/verified/.opam-switch/sources"

FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive
ARG Z3_APT_VERSION=4.8.12-3.1build1
ARG UV_VERSION=0.12.5
ARG OPAM_UID=10001

LABEL org.opencontainers.image.title="verified-rl-envs Frama-C judge" \
      org.opencontainers.image.description="Pinned ACSL-C RL verification runtime" \
      org.opencontainers.image.version="1.1.0" \
      ai.verified-rl.toolchain="frama-c=33.0;why3=1.8.2;alt-ergo=2.6.3;z3=4.8.12"

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates gcc libgmp10 python3 python3-pip zlib1g \
    "z3=${Z3_APT_VERSION}" && \
    rm -rf /var/lib/apt/lists/* && \
    pip3 install --break-system-packages --no-cache-dir "uv==${UV_VERSION}" && \
    useradd --create-home --uid "${OPAM_UID}" opam && \
    mkdir -p /workspace && \
    chown opam:opam /workspace

COPY --from=build --chown=opam:opam /home/opam/.opam /home/opam/.opam

ENV HOME=/home/opam \
    OPAMROOT=/home/opam/.opam \
    PATH=/home/opam/.opam/verified/bin:/usr/local/bin:/usr/bin:/bin \
    FRAMAC_BIN=frama-c \
    ACSL_PROVERS=alt-ergo,z3 \
    ACSL_TIMEOUT=20 \
    ACSL_TOOLCHAIN_ID="frama-c=33.0;why3=1.8.2;alt-ergo=2.6.3;z3=4.8.12;acsl-c-runner=3"

USER opam
WORKDIR /workspace
RUN why3 config detect && \
    test "$(frama-c -version)" = "33.0 (Arsenic)" && \
    why3 --version | grep -F "1.8.2" && \
    alt-ergo --version | grep -F "2.6.3" && \
    z3 --version | grep -F "4.8.12"
