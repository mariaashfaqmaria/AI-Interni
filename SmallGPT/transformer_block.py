import torch
import torch.nn as nn

from attention import MultiHeadAttention


class FeedForward(nn.Module):

    def __init__(self, embedding_dim: int):
        super().__init__()

        hidden_dim = 4 * embedding_dim

        self.network = nn.Sequential(
            nn.Linear(embedding_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, embedding_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)


class TransformerBlock(nn.Module):

    def __init__(self, embedding_dim: int, block_size: int, num_heads: int):
        super().__init__()

        self.norm_attention = nn.LayerNorm(embedding_dim)
        self.attention = MultiHeadAttention(
            embedding_dim, block_size, num_heads
        )

        self.norm_feed_forward = nn.LayerNorm(embedding_dim)
        self.feed_forward = FeedForward(embedding_dim)

    def forward(self, x):
        x = x + self.attention(self.norm_attention(x))
        x = x + self.feed_forward(self.norm_feed_forward(x))
        return x