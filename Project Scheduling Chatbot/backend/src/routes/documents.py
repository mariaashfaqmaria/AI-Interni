# backend/src/routes/documents.py
import logging
import tempfile
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from pypdf import PdfReader

from ..config import get_settings
from ..deps import get_current_user
from ..models import User
from ..services import retriever
from ..services.documents import store


# ROUTER CONFIGURATION

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)

log = logging.getLogger(__name__)

# Maximum PDF upload size: 50 MB
MAX_FILE_SIZE = 50 * 1024 * 1024

# Read upload in 1 MB blocks
UPLOAD_CHUNK_SIZE = 1024 * 1024


# DOCUMENT INFORMATION

@router.get("/info")
def info(_: User = Depends(get_current_user)):

    loaded = retriever.has_documents()

    return {
        "loaded": loaded,
        "file": retriever.filename() if loaded else None,
        "pages": len(store.pages),
        "backend": retriever.backend_name(),
    }


# PDF VALIDATION

def validate_pdf(path: Path) -> int:
    """
    Validate the uploaded PDF.

    Checks:
    1. PDF signature.
    2. PDF readability.
    3. Non-empty pages.
    4. Extractable text.

    Returns the number of PDF pages.
    """

    if not path.exists():

        raise ValueError(
            "Uploaded PDF file does not exist."
        )

    if path.stat().st_size == 0:

        raise ValueError(
            "Uploaded PDF is empty."
        )

    # Check PDF signature.
    with path.open("rb") as pdf_file:

        header = pdf_file.read(1024)

    if b"%PDF-" not in header:

        raise ValueError(
            "Invalid PDF file signature."
        )

    # Check PDF readability.
    reader = PdfReader(str(path), strict=False)

    if reader.is_encrypted:

        raise ValueError(
            "Password-protected PDFs are not supported."
        )

    if len(reader.pages) == 0:

        raise ValueError(
            "PDF contains no pages."
        )

    # Ensure that at least one page contains text.
    has_text = False

    for page in reader.pages:

        extracted_text = page.extract_text() or ""

        if extracted_text.strip():

            has_text = True
            break

    if not has_text:

        raise ValueError(
            "PDF contains no extractable text. "
            "Scanned PDFs require OCR before ingestion."
        )

    return len(reader.pages)

# PDF UPLOAD AND INGESTION

@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
):
    """
    Safely upload and ingest a PDF.

    Workflow:

        Upload PDF
            |
        Validate filename
            |
        Save temporary PDF
            |
        Check file size
            |
        Validate PDF
            |
        Ingest into retriever / Pinecone
            |
        Replace existing PDF
            |
        Return success

    The existing PDF is preserved if ingestion fails.
    """

    # STEP 1: VALIDATE FILENAME

    if not (file.filename or "").lower().endswith(".pdf"):

        await file.close()

        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    target = Path(
        get_settings().document_path
    )

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # STEP 2: CREATE TEMPORARY UPLOAD DIRECTORY

    try:

        with tempfile.TemporaryDirectory(
            prefix=".document-upload-",
            dir=str(target.parent),
        ) as temporary_directory:

            temp_path = (
                Path(temporary_directory)
                / target.name
            )

            # STEP 3: SAVE FILE IN SMALL BLOCKS

            total_size = 0

            with temp_path.open("wb") as output_file:

                while True:

                    chunk = await file.read(
                        UPLOAD_CHUNK_SIZE
                    )

                    if not chunk:
                        break

                    total_size += len(chunk)

                    if total_size > MAX_FILE_SIZE:

                        raise HTTPException(
                            status_code=413,
                            detail=(
                                "PDF exceeds the maximum "
                                "allowed upload size of 50 MB."
                            ),
                        )

                    output_file.write(chunk)

            if total_size == 0:

                raise HTTPException(
                    status_code=400,
                    detail="Uploaded PDF is empty.",
                )

            log.info(
                "Temporary PDF uploaded: %s bytes",
                total_size,
            )

            # STEP 4: VALIDATE PDF

            try:

                page_count = validate_pdf(temp_path)

            except Exception as validation_error:

                log.warning(
                    "PDF validation failed: %s",
                    validation_error,
                    exc_info=True,
                )

                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Invalid PDF: {validation_error}"
                    ),
                ) from validation_error

            log.info(
                "PDF validation successful: %s pages",
                page_count,
            )

            # STEP 5: INGEST TEMPORARY PDF

            try:

                log.info(
                    "Starting document ingestion: %s",
                    temp_path.name,
                )

                ingestion_result = retriever.ingest(
                    temp_path
                )

                log.info(
                    "Document ingestion completed successfully."
                )

            except Exception as ingestion_error:

                log.exception(
                    "Document ingestion failed."
                )

                # Restore the previous local document.
                try:

                    store.load(target)

                    log.info(
                        "Previous local document restored."
                    )

                except Exception:

                    log.exception(
                        "Could not restore previous local document."
                    )

                raise HTTPException(
                    status_code=500,
                    detail=(
                        "PDF ingestion failed. "
                        "The previous PDF was preserved. "
                        f"Reason: {ingestion_error}"
                    ),
                ) from ingestion_error

            # STEP 6: REPLACE ORIGINAL PDF ONLY AFTER SUCCESS

            try:

                temp_path.replace(target)

                # Update local store path because the
                # temporary directory will be removed.
                store.path = target

            except Exception as replacement_error:

                log.exception(
                    "Could not replace the original PDF."
                )

                # Restore previous local document.
                try:

                    store.load(target)

                except Exception:

                    log.exception(
                        "Could not restore previous document."
                    )

                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Ingestion succeeded, but the PDF "
                        "could not be moved to its final location. "
                        "Check the Pinecone namespace and "
                        "document file before retrying."
                    ),
                ) from replacement_error

            log.info(
                "PDF successfully uploaded and indexed: %s",
                target.name,
            )

            # STEP 7: RETURN SUCCESS

            return {
                "loaded": True,
                **ingestion_result,
                "file": target.name,
                "pages": page_count,
                "message": (
                    "PDF uploaded and indexed successfully."
                ),
            }

    except HTTPException:

        raise

    except Exception as error:

        log.exception(
            "Unexpected document upload error."
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Unexpected document upload error: {error}"
            ),
        ) from error

    finally:

        await file.close()
