from fastapi import FastAPI, Depends, Request, Query
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from database import get_db, engine
import models, schemas
import time
from typing import Optional
from logger import logger

models.Base.metadata.create_all(bind=engine)
app = FastAPI(title="FASTAPI CRUD with PostgreSQL")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path}?{request.url.query} - Status: {response.status_code} - Time: {process_time:.2f}s")
    return response

@app.get("/", tags=["Root"])
async def home():
    try:
        logger.info("Home called")
        return JSONResponse(status_code=200, content={"status": "success", "message": "Task 5 - Query & Path Params Enabled"})
    except Exception as e:
        logger.error(f"Home failed: {str(e)}")
        return JSONResponse(status_code=500, content={"status": "failed", "message": str(e)})

@app.post("/items", tags=["Items"])
async def create_item(item: schemas.ItemCreate, db: Session = Depends(get_db)):
    try:
        logger.info(f"Creating item: {item.name}")
        new_item = models.Item(**item.dict())
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        logger.info(f"Item created ID: {new_item.id}")
        return JSONResponse(status_code=201, content={"status": "success", "data": jsonable_encoder(new_item)})
    except Exception as e:
        db.rollback()
        logger.error(f"Create failed: {str(e)}")
        return JSONResponse(status_code=500, content={"status": "failed", "message": str(e)})

# ===== TASK 5 MAIN - QUERY PARAMETERS EXAMPLE =====
@app.get("/items", tags=["Items"])
async def get_all_items(
    db: Session = Depends(get_db),
    # --- Query Params (all optional) ---
    search: Optional[str] = Query(None, description="Search by name or description"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
    skip: int = Query(0, ge=0, description="Pagination skip"),
    limit: int = Query(10, ge=1, le=100, description="Pagination limit max 100"),
    sort_by: str = Query("id", description="Sort by: id, name, price"),
    order: str = Query("asc", description="Order: asc or desc")
):
    try:
        logger.info(f"Query Params -> search={search}, min={min_price}, max={max_price}, skip={skip}, limit={limit}, sort={sort_by} {order}")

        query = db.query(models.Item)

        # 1. Search filter (Query Param)
        if search:
            query = query.filter(models.Item.name.ilike(f"%{search}%") | models.Item.description.ilike(f"%{search}%"))

        # 2. Price filter (Query Param)
        if min_price is not None:
            query = query.filter(models.Item.price >= min_price)
        if max_price is not None:
            query = query.filter(models.Item.price <= max_price)

        # 3. Sorting (Query Param)
        if sort_by == "price":
            sort_col = models.Item.price
        elif sort_by == "name":
            sort_col = models.Item.name
        else:
            sort_col = models.Item.id

        if order == "desc":
            query = query.order_by(sort_col.desc())
        else:
            query = query.order_by(sort_col.asc())

        total = query.count()
        all_data = query.offset(skip).limit(limit).all()

        return JSONResponse(status_code=200, content={
            "status": "success",
            "total_matched": total,
            "skip": skip,
            "limit": limit,
            "count": len(all_data),
            "filters_applied": {"search": search, "min_price": min_price, "max_price": max_price},
            "data": jsonable_encoder(all_data)
        })
    except Exception as e:
        logger.error(f"Get all failed: {str(e)}")
        return JSONResponse(status_code=500, content={"status": "failed", "message": str(e)})

# ===== PATH PARAMETER EXAMPLE =====
@app.get("/items/{item_id}", tags=["Items"])
async def get_item(
    item_id: int, # <-- Path Param (mandatory)
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"Path Param -> Fetching item ID: {item_id}")
        item = db.query(models.Item).filter(models.Item.id == item_id).first()
        if not item:
            logger.warning(f"Item {item_id} not found")
            return JSONResponse(status_code=404, content={"status": "failed", "message": f"Item {item_id} not found"})
        return JSONResponse(status_code=200, content={"status": "success", "data": jsonable_encoder(item)})
    except Exception as e:
        logger.error(f"Get item {item_id} failed: {str(e)}")
        return JSONResponse(status_code=500, content={"status": "failed", "message": str(e)})

# ===== PUT WITH BOTH PATH + QUERY PARAM =====
@app.put("/items/{item_id}", tags=["Items"])
async def update_item(
    item_id: int, # Path Param: which item
    updated: schemas.ItemCreate,
    db: Session = Depends(get_db),
    notify: bool = Query(False, description="Query Param: Should notify user? true/false") # Query Param: extra option
):
    try:
        logger.info(f"Path={item_id}, Query notify={notify}")
        item = db.query(models.Item).filter(models.Item.id == item_id).first()
        if not item:
            return JSONResponse(status_code=404, content={"status": "failed", "message": f"Item {item_id} not found"})
        item.name = updated.name
        item.description = updated.description
        item.price = updated.price
        db.commit()
        db.refresh(item)
        logger.info(f"Item {item_id} updated, notify={notify}")
        return JSONResponse(status_code=200, content={"status": "success", "notify_sent": notify, "data": jsonable_encoder(item)})
    except Exception as e:
        db.rollback()
        logger.error(f"Update failed: {str(e)}")
        return JSONResponse(status_code=500, content={"status": "failed", "message": str(e)})

@app.delete("/items/{item_id}", tags=["Items"])
async def delete_item(item_id: int, db: Session = Depends(get_db)):
    try:
        item = db.query(models.Item).filter(models.Item.id == item_id).first()
        if not item:
            return JSONResponse(status_code=404, content={"status": "failed", "message": f"Item {item_id} not found"})
        db.delete(item)
        db.commit()
        logger.info(f"Item {item_id} deleted")
        return JSONResponse(status_code=200, content={"status": "success", "message": f"Item {item_id} deleted"})
    except Exception as e:
        db.rollback()
        logger.error(f"Delete failed: {str(e)}")
        return JSONResponse(status_code=500, content={"status": "failed", "message": str(e)})

@app.delete("/items", tags=["Items"])
async def delete_all_items(db: Session = Depends(get_db)):
    try:
        total = db.query(models.Item).count()
        if total == 0:
            return JSONResponse(status_code=404, content={"status": "failed", "message": "No items to delete"})
        db.query(models.Item).delete()
        db.commit()
        return JSONResponse(status_code=200, content={"status": "success", "message": f"Deleted all {total} items"})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"status": "failed", "message": str(e)})

@app.put("/items", tags=["Items"])
async def update_all_items(updated_data: schemas.ItemCreate, db: Session = Depends(get_db)):
    try:
        all_items = db.query(models.Item).all()
        if not all_items:
            return JSONResponse(status_code=404, content={"status": "failed", "message": "No items found"})
        for i in all_items:
            i.name = updated_data.name
            i.description = updated_data.description
            i.price = updated_data.price
        db.commit()
        return JSONResponse(status_code=200, content={"status": "success", "message": f"Updated {len(all_items)} items"})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"status": "failed", "message": str(e)})