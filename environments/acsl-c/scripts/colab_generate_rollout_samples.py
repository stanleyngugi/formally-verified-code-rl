"""Capture stochastic rollout candidates for harness-shape experiments.

This is intentionally generation-only: candidates are not verifier-scored here.
Each row carries the sampling seed and decoding parameters needed to replay the
same rollout on a Docker/Frama-C worker later.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from pathlib import Path


def stable_id(record: dict) -> str:
    source = record.get("reference_solution") or record.get("skeleton_c") or ""
    digest = hashlib.sha256(source.replace("\r\n", "\n").encode()).hexdigest()
    return f"casp-sha256:{digest}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--split", default="validation")
    parser.add_argument("--max-tasks", type=int, default=8)
    parser.add_argument("--num-samples", type=int, default=4)
    parser.add_argument("--model", default="unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit")
    parser.add_argument("--max-seq-length", type=int, default=2048)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.max_tasks < 1 or args.num_samples < 1:
        parser.error("--max-tasks and --num-samples must be positive")
    if not args.data.is_file():
        parser.error(f"data file does not exist: {args.data}")
    if not args.split_manifest.is_file():
        parser.error(f"split manifest does not exist: {args.split_manifest}")

    manifest = json.loads(args.split_manifest.read_text(encoding="utf-8"))
    splits = manifest.get("splits", {})
    if args.split not in splits:
        parser.error(f"unknown split {args.split!r}; available: {sorted(splits)}")
    records = [
        json.loads(line)
        for line in args.data.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    selected = set(splits[args.split])
    records = [record for record in records if stable_id(record) in selected]
    records.sort(key=stable_id)
    records = records[: args.max_tasks]
    if not records:
        raise SystemExit(
            "No records matched the requested split. Check that --data is the "
            "canonical CASP JSONL containing the split IDs."
        )

    import torch
    from huggingface_hub import model_info
    from unsloth import FastLanguageModel

    revision = model_info(args.model).sha
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.model,
        revision=revision,
        max_seq_length=args.max_seq_length,
        dtype=torch.float16,
        load_in_4bit=True,
        fast_inference=False,
    )
    # The model card carries a stale max_length=32768 default.  These
    # captures use explicit max_new_tokens, so clear it to avoid Transformers
    # treating both length controls as active (and changing nothing else).
    model.generation_config.max_length = None
    FastLanguageModel.for_inference(model)
    system = (
        "You are an expert in formally verified C programming using ACSL. "
        "Complete only the target function body. Do not modify annotations, "
        "includes, signatures, or any other code. Output only solution.c."
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as stream:
        for task_index, record in enumerate(records):
            prompt = (
                system
                + "\n\nComplete this annotated C function so every annotation verifies:\n\n"
                + record["skeleton_c"]
            )
            inputs = tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=args.max_seq_length,
            ).to("cuda")
            for sample_index in range(args.num_samples):
                sampling_seed = args.seed + task_index * args.num_samples + sample_index
                random.seed(sampling_seed)
                torch.manual_seed(sampling_seed)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed_all(sampling_seed)
                started = time.monotonic()
                with torch.inference_mode():
                    output = model.generate(
                        **inputs,
                        max_new_tokens=args.max_new_tokens,
                        do_sample=True,
                        temperature=args.temperature,
                        top_p=args.top_p,
                    )
                completion = tokenizer.decode(
                    output[0, inputs.input_ids.shape[1] :], skip_special_tokens=True
                )
                row = {
                    "task_id": stable_id(record),
                    "source_idx": record.get("idx"),
                    "split": args.split,
                    "sample_index": sample_index,
                    "sampling_seed": sampling_seed,
                    "temperature": args.temperature,
                    "top_p": args.top_p,
                    "model": args.model,
                    "revision": revision,
                    "prompt_tokens": int(inputs.input_ids.shape[1]),
                    "completion_tokens": int(
                        output.shape[1] - inputs.input_ids.shape[1]
                    ),
                    "elapsed_seconds": time.monotonic() - started,
                    "completion": completion,
                    "verifier_scored": False,
                }
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                stream.flush()
                print(
                    json.dumps({k: row[k] for k in row if k != "completion"}),
                    flush=True,
                )
                del output
            del inputs
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
