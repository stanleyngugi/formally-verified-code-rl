"""Measure generation and QLoRA optimizer-step memory; this is not an RL result.

Run each model in a fresh subprocess so allocator state cannot bias comparisons.
Results are append-only JSONL. No generated C is executed by this probe.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--sequence-length", type=int, default=2048)
    parser.add_argument(
        "--output", type=Path, default=Path("colab_probe_results.jsonl")
    )
    args = parser.parse_args()
    import torch
    import unsloth  # Must patch before transformers imports.
    from huggingface_hub import model_info
    from unsloth import FastLanguageModel

    result = {
        "model": args.model,
        "sequence_length": args.sequence_length,
        "experiment": "generation_and_qlora_optimizer_probe",
        "status": "started",
        "torch": torch.__version__,
        "unsloth": unsloth.__version__,
        "gpu": torch.cuda.get_device_name(0),
        "timestamp": time.time(),
    }
    start = time.monotonic()

    def measure(stage):
        torch.cuda.synchronize()
        free, total = torch.cuda.mem_get_info()
        result[stage] = {
            "used_gib": (total - free) / 2**30,
            "peak_allocated_gib": torch.cuda.max_memory_allocated() / 2**30,
            "peak_reserved_gib": torch.cuda.max_memory_reserved() / 2**30,
        }
        print(stage, json.dumps(result[stage]), flush=True)

    try:
        revision = model_info(args.model).sha
        result["revision"] = revision
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=args.model,
            revision=revision,
            max_seq_length=args.sequence_length,
            dtype=torch.float16,
            load_in_4bit=True,
            fast_inference=False,
        )
        # Use explicit max_new_tokens below; discard the model card's stale
        # max_length default so the probe remains warning-free and reproducible.
        model.generation_config.max_length = None
        measure("loaded")
        FastLanguageModel.for_inference(model)
        inputs = tokenizer(
            "Write a C function int max2(int a, int b) returning the larger value.\n",
            return_tensors="pt",
        ).to("cuda")
        torch.cuda.reset_peak_memory_stats()
        output = model.generate(**inputs, max_new_tokens=128, do_sample=False)
        result["generated_tokens"] = output.shape[1] - inputs.input_ids.shape[1]
        result["generated_text"] = tokenizer.decode(
            output[0, inputs.input_ids.shape[1] :]
        )
        measure("generation_memory")
        del output, inputs
        model = FastLanguageModel.get_peft_model(
            model,
            r=16,
            target_modules=[
                "q_proj",
                "k_proj",
                "v_proj",
                "o_proj",
                "gate_proj",
                "up_proj",
                "down_proj",
            ],
            lora_alpha=16,
            lora_dropout=0,
            bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=20260909,
        )
        FastLanguageModel.for_training(model)
        model.config.use_cache = False
        tokens = tokenizer(
            "int max2(int a, int b) { return a > b ? a : b; }\n" * args.sequence_length,
            truncation=True,
            max_length=args.sequence_length,
            return_tensors="pt",
        ).to("cuda")
        optimizer = torch.optim.AdamW(
            [p for p in model.parameters() if p.requires_grad], lr=1e-5
        )
        torch.cuda.reset_peak_memory_stats()
        loss = model(**tokens, labels=tokens.input_ids).loss
        loss.backward()
        assert torch.isfinite(loss), "non-finite loss"
        assert all(
            torch.isfinite(p.grad).all()
            for p in model.parameters()
            if p.grad is not None
        )
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        result["loss"] = loss.item()
        result["trainable_parameters"] = sum(
            p.numel() for p in model.parameters() if p.requires_grad
        )
        measure("optimizer_step")
        result["status"] = "passed"
    except Exception as exc:  # noqa: BLE001 - probe must persist failure diagnostics
        result["status"] = "failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
        print(result["error"], flush=True)
    finally:
        result["elapsed_seconds"] = time.monotonic() - start
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(result) + "\n")
        print("PROBE_RESULT", json.dumps(result), flush=True)
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
