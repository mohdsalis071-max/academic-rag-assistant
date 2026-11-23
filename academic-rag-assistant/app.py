"""
Academic RAG Assistant - FastAPI Application
Main entry point for local execution and Render Web Service deployment.
"""

import os
import sys
import time
import shutil
import logging
from typing import List, Optional
from pathlib import Path

# Ensure local site packages are available
import site
user_site = site.getusersitepackages()
if user_site and user_site not in sys.path:
    sys.path.insert(0, user_site)

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from document_processor import DocumentProcessor
from rag_engine import RAGEngine

# Load environment variables from .env if present
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("academic_app")

# Application base directories
BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
STORAGE_DIR = BASE_DIR / "storage"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# App startup timestamp for health metrics
START_TIME = time.time()

# Initialize core services
rag_engine = RAGEngine(storage_dir=str(STORAGE_DIR))
doc_processor = DocumentProcessor(chunk_size=750, chunk_overlap=150)

# Initialize FastAPI application
app = FastAPI(
    title="Academic RAG Assistant",
    description="Intelligent AI Academic Assistant powered by Google Gemini and Retrieval-Augmented Generation.",
    version="1.0.0"
)

# Enable CORS for cross-origin or local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Pydantic Schemas
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Student's academic question or query")
    study_mode: str = Field("general", description="Study mode: general, summarize, eli5, exam, revision, quiz")
    doc_id: Optional[str] = Field(None, description="Optional document ID to focus retrieval on")
    api_key: Optional[str] = Field(None, description="Optional Gemini API key passed from UI")


class ApiKeyRequest(BaseModel):
    api_key: str = Field(..., min_length=10, description="Gemini API Key")


# Routes
@app.get("/", summary="Serve main web interface")
async def serve_index():
    """Serves the academic assistant user interface."""
    index_path = TEMPLATES_DIR / "index.html"
    if not index_path.exists():
        return JSONResponse(
            status_code=500,
            content={"error": "Frontend template index.html not found"}
        )
    return FileResponse(str(index_path))


@app.get("/health", summary="Health check endpoint for Render monitoring")
async def health_check():
    """Returns application status, uptime, and RAG index health for Render."""
    uptime_seconds = round(time.time() - START_TIME, 2)
    stats = rag_engine.get_stats()
    return {
        "status": "healthy",
        "service": "academic-rag-assistant",
        "uptime_seconds": uptime_seconds,
        "api_key_configured": stats["api_key_configured"],
        "documents_count": stats["total_documents"],
        "chunks_count": stats["total_chunks"],
        "total_pages": stats["total_pages"],
        "models": {
            "embeddings": stats["embedding_model"],
            "generation": stats["generation_model"]
        },
        "ephemeral_storage_warning": "Render Free Tier instances use ephemeral storage; uploads reset upon server restart or re-deploy."
    }


@app.get("/download-project", summary="Download full source code as a ZIP archive")
async def download_project():
    """Provides a downloadable ZIP archive containing the complete application source code."""
    zip_path = STATIC_DIR / "academic-rag-assistant.zip"
    if not zip_path.exists():
        # Fallback to parent directory if needed
        zip_path = BASE_DIR.parent / "academic-rag-assistant.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="ZIP archive not found on server.")
    return FileResponse(
        str(zip_path),
        filename="academic-rag-assistant.zip",
        media_type="application/zip"
    )


@app.get("/stats", summary="Get knowledge base statistics")
async def get_stats():
    """Returns RAG knowledge base stats."""
    return rag_engine.get_stats()


@app.post("/api-key", summary="Set or update Gemini API key dynamically")
async def set_api_key(req: ApiKeyRequest):
    """Allows setting or testing a Gemini API key directly from the UI."""
    key = req.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="API key cannot be empty.")

    rag_engine.set_api_key(key)
    if rag_engine.is_configured():
        return {"status": "success", "message": "Gemini API key configured successfully."}
    else:
        raise HTTPException(status_code=400, detail="Invalid API key or failed to initialize Gemini client.")


@app.get("/documents", summary="List all processed academic documents")
async def list_documents():
    """Returns metadata for all documents currently indexed in the knowledge base."""
    docs = list(rag_engine.documents.values())
    return {
        "count": len(docs),
        "documents": sorted(docs, key=lambda x: x.get("uploaded_at", ""), reverse=True)
    }


@app.post("/upload", summary="Upload and index academic PDF documents")
async def upload_documents(files: List[UploadFile] = File(...)):
    """
    Accepts one or more PDF files, validates format and size, extracts text page-by-page,
    chunks content with overlap, computes embeddings with Gemini, and updates the vector store.
    """
    if not rag_engine.is_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gemini API Key is missing. Please configure GEMINI_API_KEY in Render environment variables or enter it in the website settings drawer."
        )

    if not files:
        raise HTTPException(status_code=400, detail="No files provided for upload.")

    results = []
    errors = []
    max_file_size_bytes = 25 * 1024 * 1024  # 25 MB limit for Render free tier safety

    for file in files:
        filename = file.filename or "uploaded.pdf"
        if not filename.lower().endswith(".pdf"):
            errors.append(f"'{filename}' was rejected: Only PDF files (.pdf) are supported.")
            continue

        temp_path = UPLOADS_DIR / f"temp_{int(time.time()*1000)}_{filename}"
        try:
            # Read and enforce file size limit
            content = await file.read()
            if len(content) > max_file_size_bytes:
                errors.append(f"'{filename}' exceeds the 25 MB limit for memory safety on Render Free tier.")
                continue

            if len(content) == 0:
                errors.append(f"'{filename}' is empty.")
                continue

            with open(temp_path, "wb") as f_out:
                f_out.write(content)

            # Process document: text extraction and smart chunking
            metadata, chunks = doc_processor.extract_from_pdf(str(temp_path), filename)

            # Embed chunks and add to vector store
            rag_engine.add_document(metadata, chunks)

            results.append({
                "id": metadata["id"],
                "filename": metadata["filename"],
                "total_pages": metadata["total_pages"],
                "file_size": metadata["file_size_formatted"],
                "total_chunks": metadata["total_chunks"],
                "uploaded_at": metadata["uploaded_at"]
            })

        except ValueError as val_err:
            errors.append(str(val_err))
        except Exception as ex:
            logger.error(f"Error processing file '{filename}': {ex}", exc_info=True)
            errors.append(f"Failed to process '{filename}': {str(ex)}")
        finally:
            # Remove temporary file
            if temp_path.exists():
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    return {
        "uploaded_count": len(results),
        "documents": results,
        "errors": errors,
        "total_documents_now": len(rag_engine.documents),
        "total_chunks_now": len(rag_engine.chunks)
    }


@app.delete("/documents/{document_id}", summary="Remove a document from knowledge base")
async def delete_document(document_id: str):
    """Deletes a document and its embeddings from the active knowledge base."""
    deleted = rag_engine.delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")
    return {
        "status": "success",
        "message": f"Document '{document_id}' removed successfully.",
        "remaining_documents": len(rag_engine.documents),
        "remaining_chunks": len(rag_engine.chunks)
    }


@app.post("/documents/clear", summary="Clear all documents from knowledge base")
async def clear_all_documents():
    """Clears all indexed documents and resets vector storage."""
    rag_engine.clear_all()
    return {
        "status": "success",
        "message": "All documents and vector indices have been cleared."
    }


@app.post("/chat", summary="Ask an academic question using RAG")
async def chat_rag(req: ChatRequest):
    """
    Retrieves context relevant to the user query and uses Google Gemini to generate
    an accurate, source-attributed academic response.
    """
    # If client passed an API key in the request, set it
    if req.api_key and req.api_key.strip():
        rag_engine.set_api_key(req.api_key.strip())

    if not rag_engine.is_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gemini API Key is missing. Please configure GEMINI_API_KEY in Render environment variables or enter it in the website settings drawer."
        )

    try:
        response_data = rag_engine.generate_academic_response(
            question=req.message,
            study_mode=req.study_mode,
            doc_id=req.doc_id,
            top_k=5,
            relevance_threshold=0.38
        )
        return response_data
    except Exception as ex:
        logger.error(f"Error handling chat query: {ex}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while generating the answer: {str(ex)}"
        )


if __name__ == "__main__":
    import uvicorn
    # Support Render's PORT environment variable
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting Academic RAG Assistant on port {port}...")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
