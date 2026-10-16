from collections import Counter
from pathlib import Path


class SimpleTokenizer:

    END_TOKEN = "<END>"
    UNK_TOKEN = "<UNK>"

    def __init__(self, text):
        self.text = text
        self._build_vocabulary()

    def _build_vocabulary(self):
        words = self.text.split()
        counts = Counter(words)

        vocabulary = [self.UNK_TOKEN, self.END_TOKEN]
        vocabulary.extend(sorted(word for word in counts if word not in vocabulary))

        self.stoi = {token: idx for idx, token in enumerate(vocabulary)}
        self.itos = {idx: token for token, idx in self.stoi.items()}

    @property
    def vocab_size(self):
        return len(self.stoi)

    def encode(self, text):
        return [self.stoi.get(token, self.stoi[self.UNK_TOKEN])
                for token in text.split()]

    def decode(self, ids):
        return " ".join(self.itos[int(idx)] for idx in ids)

    def save_vocabulary(self, path = "vocabulary.txt"):
        Path(path).write_text("\n".join(self.stoi.keys()), encoding="utf-8")