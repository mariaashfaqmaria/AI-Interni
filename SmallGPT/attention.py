import math

import torch
import torch.nn as nn
import torch.nn.functional as F


class SelfAttention(nn.Module):

    def __init__(self, embedding_dim, block_size, head_dim):
        super().__init__()

        self.key = nn.Linear(embedding_dim, head_dim, bias=False)
        self.query = nn.Linear(embedding_dim, head_dim, bias=False)
        self.value = nn.Linear(embedding_dim, head_dim, bias=False)

        causal_mask = torch.tril(torch.ones(block_size, block_size))
        self.register_buffer("causal_mask", causal_mask)

    def forward(self, x):
        _, sequence_length, _ = x.shape

        keys = self.key(x)
        queries = self.query(x)
        values = self.value(x)

        scores = queries @ keys.transpose(-2, -1)
        scores = scores / math.sqrt(keys.size(-1))

        mask = self.causal_mask[:sequence_length, :sequence_length]
        scores = scores.masked_fill(mask == 0, float("-inf"))

        attention_weights = F.softmax(scores, dim=-1)

        return attention_weights @ values


class MultiHeadAttention(nn.Module):

    def __init__(self, embedding_dim, block_size, num_heads):
        super().__init__()

        if embedding_dim % num_heads != 0:
            raise ValueError("embedding_dim must be divisible by num_heads.")

        head_dim = embedding_dim // num_heads

        self.heads = nn.ModuleList(
            [
                SelfAttention(embedding_dim, block_size, head_dim)
                for _ in range(num_heads)
            ]
        )

        self.output_projection = nn.Linear(embedding_dim, embedding_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        combined = torch.cat([head(x) for head in self.heads], dim=-1)
        return self.output_projection(combined)
