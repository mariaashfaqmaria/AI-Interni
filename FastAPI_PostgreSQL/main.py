
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import (
    FastAPI,
    Depends,
    Request,
    Query,
    UploadFile,
    File,
    Form,
)
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from database import get_db, engine
import models
import schemas
from logger import logger
from settings import settings


# Application setup

models.Base.metadata.create_all(bind=engine)

#app = FastAPI(title="FASTAPI CRUD with PostgreSQL")

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# Request logging middleware

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time

    logger.info(
        f"{request.method} {request.url.path} "
        f"Status: {response.status_code} "
        f"Time: {process_time:.2f}s"
    )

    return response


# Root endpoint

@app.get("/", tags=["Root"])
async def home():
    logger.info("Home endpoint called")

    return {
        "status": "success",
        "message": "FASTAPI CRUD with PostgreSQL"
    }

# Configuration endpoint

PUBLIC_SETTINGS = {
    "APP_NAME": "app_name",
    "DEBUG": "debug",
    "MAX_UPLOAD_SIZE": "max_upload_size",
    "WELCOME_MESSAGE": "welcome_message",
}

# Configuration endpoint
@app.get("/config/{key}", tags=["Configuration"])
async def get_config_value(key: str):
    attribute = PUBLIC_SETTINGS.get(key.upper())

    if attribute is None:
        return JSONResponse(
            status_code=404,
            content={
                "status": "failed",
                "message": (
                    "Configuration variable not found "
                    "or not accessible"
                ),
            },
        )

    return {
        "status": "success",
        "key": key.upper(),
        "value": getattr(settings, attribute),
    }


# Simple file upload

@app.post("/upload", tags=["File Upload"])
async def upload_file(file: UploadFile = File(...)):
    file_path = None

    try:
        original_name = Path(
            file.filename or "uploaded_file"
        ).name

        saved_name = f"{uuid.uuid4().hex}_{original_name}"
        file_path = UPLOAD_DIR / saved_name

        with file_path.open("wb") as destination:
            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                destination.write(chunk)

        logger.info(f"File uploaded: {saved_name}")

        return JSONResponse(
            status_code=201,
            content={
                "status": "success",
                "message": "File uploaded successfully",
                "original_filename": original_name,
                "saved_filename": saved_name,
                "saved_path": str(file_path)
            }
        )

    except Exception:
        logger.exception("Simple file upload failed")

        # Remove an incomplete file if saving failed.
        if file_path is not None:
            try:
                file_path.unlink(missing_ok=True)
            except OSError:
                logger.exception("Could not remove incomplete upload")

        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": "File upload failed"
            }
        )

    finally:
        await file.close()


# File upload with additional parameters

@app.post("/upload-with-params", tags=["File Upload"])
async def upload_file_with_params(
    file: UploadFile = File(...),
    description: str = Form(
        ...,
        min_length=1,
        max_length=500
    ),
    category: str = Form(
        default="general",
        max_length=50
    ),
    process_file: bool = Form(default=False)
):
    file_path = None

    try:
        # Get a safe filename without directory components.
        original_name = Path(
            file.filename or "uploaded_file"
        ).name

        # Avoid overwriting another uploaded file.
        saved_name = f"{uuid.uuid4().hex}_{original_name}"
        file_path = UPLOAD_DIR / saved_name

        # Save the file in chunks.
        with file_path.open("wb") as destination:
            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                destination.write(chunk)

        logger.info(
            f"File uploaded with parameters: {saved_name}; "
            f"category={category}; "
            f"process_file={process_file}"
        )

        return JSONResponse(
            status_code=201,
            content={
                "status": "success",
                "message": (
                    "File and parameters received successfully"
                ),
                "file": {
                    "original_filename": original_name,
                    "saved_filename": saved_name,
                    "saved_path": str(file_path)
                },
                "parameters": {
                    "description": description,
                    "category": category,
                    "process_file": process_file
                }
            }
        )

    except Exception:
        logger.exception("File upload with parameters failed")

        # Remove an incomplete file if saving failed.
        if file_path is not None:
            try:
                file_path.unlink(missing_ok=True)
            except OSError:
                logger.exception("Could not remove incomplete upload")

        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": "File upload failed"
            }
        )

    finally:
        await file.close()


# Create a new item

@app.post("/items", tags=["Items"])
async def create_item(
    item: schemas.ItemCreate,
    db: Session = Depends(get_db)
):
    try:
        new_item = models.Item(**item.model_dump())

        db.add(new_item)
        db.commit()
        db.refresh(new_item)

        logger.info(f"Item created: ID {new_item.id}")

        return JSONResponse(
            status_code=201,
            content={
                "status": "success",
                "data": jsonable_encoder(new_item)
            }
        )

    except Exception:
        db.rollback()
        logger.exception("Create item failed")

        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": "Could not create item"
            }
        )



# Get all items with optional filters, pagination, and sorting

@app.get("/items", tags=["Items"])
async def get_all_items(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(
        None,
        description="Search by name or description"
    ),
    min_price: Optional[float] = Query(
        None,
        description="Minimum price"
    ),
    max_price: Optional[float] = Query(
        None,
        description="Maximum price"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query("id"),
    order: str = Query("asc")
):
    try:
        if (
            min_price is not None
            and max_price is not None
            and min_price > max_price
        ):
            return JSONResponse(
                status_code=422,
                content={
                    "status": "failed",
                    "message": "min_price cannot exceed max_price"
                }
            )

        if sort_by not in {"id", "name", "price"}:
            return JSONResponse(
                status_code=422,
                content={
                    "status": "failed",
                    "message": "sort_by must be id, name, or price"
                }
            )

        if order not in {"asc", "desc"}:
            return JSONResponse(
                status_code=422,
                content={
                    "status": "failed",
                    "message": "order must be asc or desc"
                }
            )

        query = db.query(models.Item)

        if search:
            query = query.filter(
                models.Item.name.ilike(f"%{search}%")
                | models.Item.description.ilike(f"%{search}%")
            )

        if min_price is not None:
            query = query.filter(
                models.Item.price >= min_price
            )

        if max_price is not None:
            query = query.filter(
                models.Item.price <= max_price
            )

        sort_column = {
            "id": models.Item.id,
            "name": models.Item.name,
            "price": models.Item.price
        }[sort_by]

        if order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        total = query.count()
        items = query.offset(skip).limit(limit).all()

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "total_matched": total,
                "skip": skip,
                "limit": limit,
                "count": len(items),
                "filters_applied": {
                    "search": search,
                    "min_price": min_price,
                    "max_price": max_price
                },
                "data": jsonable_encoder(items)
            }
        )

    except Exception:
        logger.exception("Get all items failed")

        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": "Could not retrieve items"
            }
        )


# Get one item by ID

@app.get("/items/{item_id}", tags=["Items"])
async def get_item(
    item_id: int,
    db: Session = Depends(get_db)
):
    try:
        item = (
            db.query(models.Item)
            .filter(models.Item.id == item_id)
            .first()
        )

        if not item:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "failed",
                    "message": f"Item {item_id} not found"
                }
            )

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "data": jsonable_encoder(item)
            }
        )

    except Exception:
        logger.exception(f"Get item {item_id} failed")

        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": "Could not retrieve item"
            }
        )


# Update one item

@app.put("/items/{item_id}", tags=["Items"])
async def update_item(
    item_id: int,
    updated: schemas.ItemCreate,
    db: Session = Depends(get_db),
    notify: bool = Query(False)
):
    try:
        item = (
            db.query(models.Item)
            .filter(models.Item.id == item_id)
            .first()
        )

        if not item:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "failed",
                    "message": f"Item {item_id} not found"
                }
            )

        item.name = updated.name
        item.description = updated.description
        item.price = updated.price

        db.commit()
        db.refresh(item)

        logger.info(f"Item {item_id} updated; notify={notify}")

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "notify_sent": notify,
                "data": jsonable_encoder(item)
            }
        )

    except Exception:
        db.rollback()
        logger.exception("Update item failed")

        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": "Could not update item"
            }
        )



# Delete one item


@app.delete("/items/{item_id}", tags=["Items"])
async def delete_item(
    item_id: int,
    db: Session = Depends(get_db)
):
    try:
        item = (
            db.query(models.Item)
            .filter(models.Item.id == item_id)
            .first()
        )

        if not item:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "failed",
                    "message": f"Item {item_id} not found"
                }
            )

        db.delete(item)
        db.commit()

        logger.info(f"Item {item_id} deleted")

        return {
            "status": "success",
            "message": f"Item {item_id} deleted"
        }

    except Exception:
        db.rollback()
        logger.exception("Delete item failed")

        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": "Could not delete item"
            }
        )



# Delete all items


@app.delete("/items", tags=["Items"])
async def delete_all_items(
    db: Session = Depends(get_db)
):
    try:
        total = db.query(models.Item).count()

        if total == 0:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "failed",
                    "message": "No items to delete"
                }
            )

        db.query(models.Item).delete(
            synchronize_session=False
        )
        db.commit()

        logger.info(f"Deleted all {total} items")

        return {
            "status": "success",
            "message": f"Deleted all {total} items"
        }

    except Exception:
        db.rollback()
        logger.exception("Delete all items failed")

        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": "Could not delete items"
            }
        )



# Update all items


@app.put("/items", tags=["Items"])
async def update_all_items(
    updated_data: schemas.ItemCreate,
    db: Session = Depends(get_db)
):
    try:
        total = db.query(models.Item).update(
            {
                models.Item.name: updated_data.name,
                models.Item.description: updated_data.description,
                models.Item.price: updated_data.price
            },
            synchronize_session=False
        )

        if total == 0:
            db.rollback()

            return JSONResponse(
                status_code=404,
                content={
                    "status": "failed",
                    "message": "No items found"
                }
            )

        db.commit()

        logger.info(f"Updated all {total} items")

        return {
            "status": "success",
            "message": f"Updated {total} items"
        }

    except Exception:
        db.rollback()
        logger.exception("Update all items failed")

        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": "Could not update items"
            }
        )