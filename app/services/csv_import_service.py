import csv
import io
import logging
from typing import List, Tuple, Dict, Any, Optional
from fastapi import UploadFile, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.review import Review
from app.schemas.review import CsvImportResponse, CsvImportRowError
from app.services.project_service import get_project_by_id

logger = logging.getLogger(__name__)


async def validate_and_read_csv_file(file: UploadFile) -> str:
    """
    Read uploaded file content while enforcing file size limits and encoding constraints.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a filename",
        )

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. File must be a .csv file",
        )

    # Read content with size check
    chunks = []
    total_bytes = 0
    max_bytes = settings.max_upload_size_bytes

    while chunk := await file.read(1024 * 1024):  # 1MB chunks
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB",
            )
        chunks.append(chunk)

    raw_bytes = b"".join(chunks)
    if len(raw_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded CSV file is empty",
        )

    # Decode utf-8 with clean error handling
    try:
        content = raw_bytes.decode("utf-8-sig")  # Handles optional UTF-8 BOM
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file encoding. Uploaded CSV must be encoded in UTF-8",
        )

    return content


def process_csv_import(db: Session, project_id: int, csv_content: str) -> CsvImportResponse:
    """
    Parse CSV content, validate rows, and execute an atomic transactional insert.
    If ANY row fails validation, no rows are persisted (strict atomic import).
    """
    # 1. Verify project exists
    project = get_project_by_id(db, project_id)

    # 2. Parse CSV
    string_io = io.StringIO(csv_content.strip())
    try:
        reader = csv.reader(string_io)
        header = next(reader, None)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed CSV content: {str(exc)}",
        )

    if not header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded CSV file contains no header row",
        )

    # Normalize header column names
    col_map: Dict[str, int] = {}
    for idx, col in enumerate(header):
        cleaned_col = col.strip().lower()
        if cleaned_col:
            col_map[cleaned_col] = idx

    # Check required columns
    required_cols = ["rating", "review_text"]
    missing_cols = [c for c in required_cols if c not in col_map]
    if missing_cols:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required CSV column(s): {', '.join(missing_cols)}",
        )

    rating_idx = col_map["rating"]
    text_idx = col_map["review_text"]
    customer_idx = col_map.get("customer_name")

    rows_to_insert: List[Review] = []
    errors: List[CsvImportRowError] = []
    total_data_rows = 0

    for row_idx, row in enumerate(reader, start=1):
        total_data_rows += 1
        if total_data_rows > settings.MAX_CSV_ROWS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File exceeds maximum allowed limit of {settings.MAX_CSV_ROWS} data rows",
            )

        # Check if row has enough fields
        if len(row) <= max(rating_idx, text_idx):
            errors.append(
                CsvImportRowError(
                    row_number=row_idx,
                    column=None,
                    error=f"Row has {len(row)} columns, expected at least {max(rating_idx, text_idx) + 1}",
                )
            )
            continue

        # Validate rating
        raw_rating = row[rating_idx].strip()
        parsed_rating: Optional[int] = None
        if not raw_rating:
            errors.append(
                CsvImportRowError(
                    row_number=row_idx,
                    column="rating",
                    error="Rating is required and cannot be empty",
                )
            )
        else:
            try:
                parsed_rating = int(raw_rating)
                if parsed_rating < 1 or parsed_rating > 5:
                    errors.append(
                        CsvImportRowError(
                            row_number=row_idx,
                            column="rating",
                            error=f"Rating must be an integer between 1 and 5, received '{raw_rating}'",
                        )
                    )
            except ValueError:
                errors.append(
                    CsvImportRowError(
                        row_number=row_idx,
                        column="rating",
                        error=f"Rating must be a valid integer, received '{raw_rating}'",
                    )
                )

        # Validate review_text
        raw_text = row[text_idx].strip()
        if not raw_text:
            errors.append(
                CsvImportRowError(
                    row_number=row_idx,
                    column="review_text",
                    error="Review text cannot be empty or whitespace only",
                )
            )

        # Validate customer_name
        customer_name = None
        if customer_idx is not None and len(row) > customer_idx:
            raw_cust = row[customer_idx].strip()
            if raw_cust:
                if len(raw_cust) > 100:
                    errors.append(
                        CsvImportRowError(
                            row_number=row_idx,
                            column="customer_name",
                            error=f"Customer name exceeds maximum length of 100 characters ({len(raw_cust)})",
                        )
                    )
                else:
                    customer_name = raw_cust

        # If this row is valid and we haven't encountered prior errors, queue it
        if parsed_rating is not None and 1 <= parsed_rating <= 5 and raw_text and not any(e.row_number == row_idx for e in errors):
            rows_to_insert.append(
                Review(
                    project_id=project_id,
                    customer_name=customer_name,
                    rating=parsed_rating,
                    review_text=raw_text,
                )
            )

    # Atomic policy: if ANY row fails, reject entire batch and persist 0 records
    if errors:
        result = CsvImportResponse(
            project_id=project_id,
            total_rows=total_data_rows,
            imported_records=0,
            rejected_records=total_data_rows,
            errors=errors,
            message=f"Import failed: {len(errors)} validation error(s) found across {total_data_rows} data rows. No records were persisted.",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.model_dump(),
        )

    # Handle file with 0 data rows
    if total_data_rows == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file contains a header but no data rows",
        )

    # Persist all records atomically in a transaction
    try:
        db.add_all(rows_to_insert)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("Failed to commit CSV imported records: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist records to the database. Transaction was rolled back.",
        )

    return CsvImportResponse(
        project_id=project_id,
        total_rows=total_data_rows,
        imported_records=len(rows_to_insert),
        rejected_records=0,
        errors=[],
        message=f"Successfully imported {len(rows_to_insert)} review(s) into project {project.name}.",
    )
