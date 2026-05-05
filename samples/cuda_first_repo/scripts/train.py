"""
Fine-tuning training script for Qwen2.5 on a coding dataset.
Intentionally uses CUDA-specific APIs so ROCmPort AI has meaningful
patterns to detect and patch.
"""

import os
import torch
from torch.utils.data import DataLoader, TensorDataset
from transformers import AutoModelForCausalLM, AutoTokenizer

# ── CUDA-specific patterns that ROCmPort will flag ─────────────────────────
os.environ["CUDA_VISIBLE_DEVICES"] = "0"          # should → HIP_VISIBLE_DEVICES
os.environ["CUDA_HOME"] = "/usr/local/cuda"        # should be removed / replaced

MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"

device = torch.device("cuda")                      # hardcoded CUDA device
print("CUDA available:", torch.cuda.is_available())


def get_dummy_batch(seq_len: int = 64, batch_size: int = 4):
    ids = torch.randint(0, 1000, (batch_size, seq_len))
    labels = ids.clone()
    return ids, labels


def train(epochs: int = 3, lr: float = 2e-5):
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID).cuda()   # .cuda() call

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)

    ids, labels = get_dummy_batch()
    ids = ids.to("cuda")        # hardcoded "cuda" string
    labels = labels.to("cuda")  # hardcoded "cuda" string

    dataset = TensorDataset(ids, labels)
    loader = DataLoader(dataset, batch_size=2)

    model.train()
    for epoch in range(epochs):
        for batch_ids, batch_labels in loader:
            batch_ids = batch_ids.cuda()    # another .cuda() call
            batch_labels = batch_labels.cuda()
            outputs = model(input_ids=batch_ids, labels=batch_labels)
            loss = outputs.loss
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
        print(f"Epoch {epoch+1}/{epochs}  loss={loss.item():.4f}")

    model.save_pretrained("./qwen-finetuned")
    tokenizer.save_pretrained("./qwen-finetuned")
    print("Model saved to ./qwen-finetuned")


if __name__ == "__main__":
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU required for training")
    train()
