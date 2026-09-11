#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update >> /tmp/judge_setup.log 2>&1
add-apt-repository -y universe >> /tmp/judge_setup.log 2>&1 || true
apt-get update >> /tmp/judge_setup.log 2>&1

for pkg in libgmp-dev graphviz m4 pkg-config unzip rsync bubblewrap jq z3 opam git curl; do
  apt-get install -y -qq "$pkg" >> /tmp/judge_setup.log 2>&1 || echo "PKG_FAIL=$pkg" >> /tmp/judge_setup.log
done

command -v opam || { echo "OPAM_MISSING" >> /tmp/judge_setup.log; exit 1; }

export OPAMYES=1
opam init --disable-sandboxing -y --bare >> /tmp/judge_setup.log 2>&1 || true
J=$(( $(nproc) > 32 ? 32 : $(nproc) ))
opam switch create acsl-c ocaml-base-compiler.4.14.2 -y >> /tmp/judge_setup.log 2>&1 || true
eval "$(opam env --switch acsl-c)"
opam install -y -j "$J" frama-c.33.0 why3.1.8.2 alt-ergo.2.6.3 >> /tmp/judge_setup.log 2>&1
eval "$(opam env --switch acsl-c)"
echo "FRAMAC_VERSION=$(frama-c -version)" >> /tmp/judge_setup.log
echo "WHY3_VERSION=$(why3 --version)" >> /tmp/judge_setup.log
echo "ALTERGO_VERSION=$(alt-ergo --version | head -1)" >> /tmp/judge_setup.log
echo "Z3=$(z3 --version)" >> /tmp/judge_setup.log
test "$(frama-c -version)" = "33.0 (Arsenic)"
echo "JUDGE_SETUP_DONE" >> /tmp/judge_setup.log
