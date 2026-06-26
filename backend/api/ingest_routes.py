from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
import logging

from smart_rag.ingest import (
    ingest_raw_text,
    ingest_file_content,
    get_current_sources,
    clear_all_sources
)

logger = logging.getLogger(__name__)

ingest_router = APIRouter(prefix="/ingest", tags=["Ingestion"])


class RawTextInput(BaseModel):
    text: str = Field(..., description="Text content to ingest")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "This is a sample text.\nIt can have multiple lines.\nAnd paragraphs too."
            }
        }


@ingest_router.post("/upload-text")
def upload_and_ingest(payload: RawTextInput):
    """Upload and ingest raw text"""
    try:
        result = ingest_raw_text(payload.text, source_name="text_upload")
        
        # Handle duplicate case
        if result.get("duplicate", False):
            return {
                "success": False,
                "duplicate": True,
                "message": result["message"],
                "existing_source": result.get("existing_source"),
                "details": {
                    "current_sources": result["current_sources"],
                    "max_sources": result["max_sources"]
                }
            }
        
        return {
            "success": True,
            "duplicate": False,
            "message": result["message"],
            "details": {
                "chunks_added": result["chunks_added"],
                "current_sources": result["current_sources"],
                "max_sources": result["max_sources"],
                "removed_source": result.get("removed_source"),
                "source_id": result["source_id"]
            }
        }

    except ValueError as e:
        logger.error(f"Validation error during text ingestion: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Unexpected error during text ingestion: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}"
        )


@ingest_router.post("/upload-file")
async def upload_file(file: UploadFile = File(...)):
    """Upload and ingest a file (.txt, .pdf, .docx)"""
    try:
        # Clear previous data so answers come only from the new file
        clear_all_sources()

        content = await file.read()
        result = ingest_file_content(content, file.filename)

        # Handle duplicate case
        if result.get("duplicate", False):
            return {
                "success": False,
                "duplicate": True,
                "message": result["message"],
                "filename": file.filename,
                "existing_source": result.get("existing_source"),
                "details": {
                    "current_sources": result["current_sources"],
                    "max_sources": result["max_sources"]
                }
            }

        return {
            "success": True,
            "duplicate": False,
            "message": result["message"],
            "filename": file.filename,
            "details": {
                "chunks_added": result["chunks_added"],
                "current_sources": result["current_sources"],
                "max_sources": result["max_sources"],
                "removed_source": result.get("removed_source"),
                "source_id": result["source_id"]
            }
        }

    except ValueError as e:
        logger.error(f"Validation error for file {file.filename}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Unexpected error during file ingestion of {file.filename}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"File ingestion failed: {str(e)}"
        )


@ingest_router.get("/sources")
def list_sources():
    """Get list of currently stored sources"""
    try:
        result = get_current_sources()
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Error retrieving sources: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve sources: {str(e)}"
        )


@ingest_router.delete("/clear-all")
def clear_all():
    """Clear all sources and reset vector store"""
    try:
        result = clear_all_sources()
        return {
            "success": True,
            "message": result
        }
    except Exception as e:
        logger.error(f"Error clearing sources: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear sources: {str(e)}"
        )
        