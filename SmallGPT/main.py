from pathlib import Path
import random

import torch

from model import MiniGPT
from tokenizer import SimpleTokenizer
from training import create_training_data, train_model

DATA_FILE = Path("data.txt")

BLOCK_SIZE = 6
EMBEDDING_DIM = 32
NUM_HEADS = 2
NUM_LAYERS = 2

BATCH_SIZE = 16
LEARNING_RATE = 1e-3
TRAINING_STEPS = 1500

SEED = 42


def load_dataset(path: Path):
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path.resolve()}"
        )

    # Each non-empty line is treated as one short training sentence.
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    # <END> separates examples while keeping the dataset plain text.
    return " ".join(f"{line} <END>" for line in lines)


def main():
    random.seed(SEED)
    torch.manual_seed(SEED)

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    print("=" * 55)
    print("MiniGPT - Small Transformer Language Model")
    print("=" * 55)
    print(f"PyTorch: {torch.__version__}")
    print(f"Device : {device}")

    text = load_dataset(DATA_FILE)

    tokenizer = SimpleTokenizer(text)
    data = create_training_data(tokenizer, text)

    print(f"Vocabulary size: {tokenizer.vocab_size}")
    print(f"Training tokens: {len(data)}")

    model = MiniGPT(
        vocab_size=tokenizer.vocab_size,
        block_size=BLOCK_SIZE,
        embedding_dim=EMBEDDING_DIM,
        num_heads=NUM_HEADS,
        num_layers=NUM_LAYERS,
    ).to(device)

    parameter_count = sum(p.numel() for p in model.parameters())
    print(f"Model parameters: {parameter_count:,}")

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
    )

    print("\nStarting training...\n")

    train_model(
        model=model,
        data=data,
        optimizer=optimizer,
        block_size=BLOCK_SIZE,
        batch_size=BATCH_SIZE,
        steps=TRAINING_STEPS,
        device=device,
    )

    start_id = tokenizer.stoi.get("language", tokenizer.stoi["<UNK>"])
    context = torch.tensor([[start_id]], dtype=torch.long, device=device)

    generated = model.generate(
        context,
        max_new_tokens=15,
    )

    print("\nGenerated text:")
    print(tokenizer.decode(generated[0].tolist()))


if __name__ == "__main__":
    main()