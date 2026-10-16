from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from typing import List


app = FastAPI(title="User Management CRUD API")


#Schema definitions

class ItemBase(BaseModel):
    name: str
    description: str | None = None
    price: float


class ItemCreate(ItemBase):
    pass


class Item(ItemBase):
    id: int

#List of items to store in memory

items: List[Item] = []

next_id = 1


#Read all items

@app.get("/items", response_model=List[Item])
def get_items():

    return items

#Read one item

@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: int):

    for item in items:

        if item.id == item_id:
            return item

    raise HTTPException(
        status_code=404,
        detail="Item not found"
    )

#Create item

@app.post("/items", response_model=Item, status_code=201)
def create_item(item: ItemCreate):

    global next_id

    new_item = Item(
        id=next_id,
        **item.model_dump()
    )

    items.append(new_item)

    next_id += 1

    return new_item

#Update one item

@app.put("/items/{item_id}", response_model=Item)
def update_item(item_id: int, item: ItemCreate):

    for index, existing_item in enumerate(items):

        if existing_item.id == item_id:

            updated_item = Item(
                id=item_id,
                **item.model_dump()
            )

            items[index] = updated_item

            return updated_item

    raise HTTPException(
        status_code=404,
        detail="Item not found"
    )

#Update all items

@app.put("/items", response_model=List[Item])
def update_all_items(updated_items: List[ItemCreate]):

    if len(items) == 0:

        raise HTTPException(
            status_code=404,
            detail="No items available to update"
        )

    if len(updated_items) != len(items):

        raise HTTPException(
            status_code=400,
            detail="Number of updated items must match the number of existing items"
        )

    new_items = []

    for index, existing_item in enumerate(items):

        updated_item = Item(
            id=existing_item.id,
            **updated_items[index].model_dump()
        )

        new_items.append(updated_item)

    items.clear()
    items.extend(new_items)

    return items

#Delete one item

@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int):

    for index, item in enumerate(items):

        if item.id == item_id:

            items.pop(index)

            return Response(status_code=204)

    raise HTTPException(
        status_code=404,
        detail="Item not found"
    )

#Delete all items

@app.delete("/items", status_code=204)
def delete_all_items():

    if len(items) == 0:

        raise HTTPException(
            status_code=404,
            detail="No items available to delete"
        )

    items.clear()

    return Response(status_code=204)