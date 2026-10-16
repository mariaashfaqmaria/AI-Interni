import torch


def create_training_data(tokenizer, text):
    token_ids = tokenizer.encode(text)
    return torch.tensor(token_ids, dtype=torch.long)


def get_batch(
    data,
    block_size,
    batch_size,
    device,
):
    if len(data) <= block_size:
        raise ValueError(
            "The dataset must contain more tokens than block_size."
        )

    start_positions = torch.randint(
        low=0,
        high=len(data) - block_size,
        size=(batch_size,),
    )

    inputs = torch.stack(
        [data[start:start + block_size] for start in start_positions]
    )

    targets = torch.stack(
        [data[start + 1:start + block_size + 1] for start in start_positions]
    )

    return inputs.to(device), targets.to(device)


def train_model(
    model,
    data,
    optimizer,
    block_size,
    batch_size,
    steps,
    device,
    log_every=100,
):
    model.train()

    for step in range(steps):
        inputs, targets = get_batch(
            data=data,
            block_size=block_size,
            batch_size=batch_size,
            device=device,
        )

        _, loss = model(inputs, targets)

        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()

        if step % log_every == 0 or step == steps - 1:
            print(f"Step {step + 1:4d}/{steps} | loss: {loss.item():.4f}")
