import torch
import torch.nn as nn
import torch.nn.functional as F

from embedding import TokenAndPositionEmbedding
from transformer_block import TransformerBlock


class MiniGPT(nn.Module):
    def __init__(
        self,
        vocab_size,
        block_size,
        embedding_dim,
        num_heads,
        num_layers,
    ):
        super().__init__()

        self.block_size = block_size

        self.embedding = TokenAndPositionEmbedding(
            vocab_size=vocab_size,
            embedding_dim=embedding_dim,
            max_sequence_length=block_size,
        )

        self.transformer = nn.Sequential(
            *[
                TransformerBlock(
                    embedding_dim=embedding_dim,
                    block_size=block_size,
                    num_heads=num_heads,
                )
                for _ in range(num_layers)
            ]
        )

        self.final_norm = nn.LayerNorm(embedding_dim)
        self.language_head = nn.Linear(embedding_dim, vocab_size)

    def forward(self, token_ids, targets=None):
        x = self.embedding(token_ids)
        x = self.transformer(x)
        x = self.final_norm(x)

        logits = self.language_head(x)
        loss = None

        if targets is not None:
            batch_size, sequence_length, vocab_size = logits.shape

            logits_flat = logits.reshape(
                batch_size * sequence_length, vocab_size
            )
            targets_flat = targets.reshape(batch_size * sequence_length)

            loss = F.cross_entropy(logits_flat, targets_flat)

        return logits, loss

    @torch.no_grad()
    def generate(self, token_ids, max_new_tokens):
        self.eval()

        for _ in range(max_new_tokens):
            context = token_ids[:, -self.block_size:]

            logits, _ = self(context)
            next_token_logits = logits[:, -1, :]

            probabilities = F.softmax(next_token_logits, dim=-1)
            next_token = torch.multinomial(probabilities, num_samples=1)

            token_ids = torch.cat([token_ids, next_token], dim=1)

        return token_ids