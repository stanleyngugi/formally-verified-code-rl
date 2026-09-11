#!/usr/bin/env bash
# opam-based frama-c + alt-ergo install (no root required).
# Prereqs (one-time, via sudo): why3 z3 libgmp-dev gcc m4 pkg-config unzip rsync git bubblewrap opam
set -euo pipefail

LOG=/tmp/opam_framac_install.log
exec > >(tee -a "$LOG") 2>&1

echo "== opam init =="
opam init --disable-sandboxing -y --bare 2>/dev/null || true
opam switch create acsl-c ocaml-base-compiler.4.14.2 -y || true
eval "$(opam env --switch acsl-c)"

J=$(( $(nproc) > 4 ? 4 : $(nproc) ))

echo "== installing pinned verifier stack (-j $J) =="
opam install -y -j "$J" frama-c.33.0 why3.1.8.2 alt-ergo.2.6.3

echo "== verifying =="
which frama-c alt-ergo
frama-c -version
alt-ergo --version
echo "== INSTALL COMPLETE =="
