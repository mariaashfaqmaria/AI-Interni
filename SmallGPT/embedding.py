import torch
import torch.nn as nn


class TokenAndPositionEmbedding(nn.Module):
    def __init__(self, vocab_size, embedding_dim, max_sequence_length):
        super().__init__()

        self.token_embedding = nn.Embedding(vocab_size, embedding_dim)
        self.position_embedding = nn.Embedding(max_sequence_length, embedding_dim)

    def forward(self, token_ids):
        _, sequence_length = token_ids.shape

        positions = torch.arange(
            sequence_length,
            device=token_ids.device
        )

        token_vectors = self.token_embedding(token_ids)
        position_vectors = self.position_embedding(positions)

        return token_vectors + position_vectors
