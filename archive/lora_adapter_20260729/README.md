---
license: apache-2.0
language:
  - en
  - zh
base_model: TinyLlama/TinyLlama-1.1B-Chat-v1.0
tags:
  - sases
  - self-evolving
  - lora
---

# SASES LoRA Adapter v0.1

This LoRA adapter is the first trained weight for the SASES self-evolving system. It was fine-tuned on 79 manually verified trajectories covering Python code generation, math proofs, logic reasoning, and more.

## Usage

```python
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

base_model = AutoModelForCausalLM.from_pretrained("TinyLlama/TinyLlama-1.1B-Chat-v1.0")
model = PeftModel.from_pretrained(base_model, "sases/sases-lora-v0.1")