#!/usr/bin/env bash
cd /workspace/prime-rl
git submodule deinit -f deps/pydantic-config >> /tmp/submod3.log 2>&1
rm -rf .git/modules/deps/pydantic-config >> /tmp/submod3.log 2>&1
git submodule update --init --recursive deps/pydantic-config >> /tmp/submod3.log 2>&1
echo "EXIT=$?" >> /tmp/submod3.log
ls deps/pydantic-config >> /tmp/submod3.log 2>&1
tail -3 /tmp/submod3.log
