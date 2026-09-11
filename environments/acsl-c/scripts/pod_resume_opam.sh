#!/usr/bin/env bash
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq zlib1g-dev >> /tmp/judge_setup.log 2>&1
export OPAMYES=1
eval $(opam env) 2>/dev/null
opam install -y -j 32 frama-c alt-ergo >> /tmp/judge_setup.log 2>&1
eval $(opam env)
echo "FRAMAC_VERSION=$(frama-c -version)" >> /tmp/judge_setup.log
echo "OPAM_RESUME_DONE" >> /tmp/judge_setup.log
