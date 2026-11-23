"""
Document Processor Module for Academic RAG Assistant.
Handles PDF extraction, cleaning, metadata generation, and text chunking with page number tracking.
"""

import os
import re
import uuid
from datetime import datetime
from typing import List, Dict, Any, Tuple
import pymupdf


class DocumentProcessor:
    def __init__(self, chunk_size: int = 700, chunk_overlap: int = 150):
        """
        Initialize the DocumentProcessor.
        :param chunk_size: Target character length per chunk.
        :param chunk_overlap: Overlapping character length between consecutive chunks.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def clean_text(self, text: str) -> str:
        """
        Cleans extracted text by normalizing whitespace, line breaks, and hyphenated line ends.
        """
        if not text:
            return ""
        # Remove null bytes or control characters except standard whitespace
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        # Fix hyphenated words at line breaks (e.g. "aca-\ndemic" -> "academic")
        text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
        # Replace multiple spaces with a single space
        text = re.sub(r'[ \t]+', ' ', text)
        # Normalize multiple newlines to double newline
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def extract_from_pdf(self, file_path: str, original_filename: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Extracts text page-by-page from a PDF file using PyMuPDF and produces structured chunks.
        :param file_path: Path to the PDF file on disk.
        :param original_filename: Original name of the uploaded PDF file.
        :return: (document_metadata, list_of_chunks)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found at: {file_path}")

        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        file_size_bytes = os.path.getsize(file_path)

        doc = pymupdf.open(file_path)
        total_pages = len(doc)
        total_characters = 0
        pages_content = []

        for page_idx in range(total_pages):
            page_num = page_idx + 1
            page = doc[page_idx]
            raw_text = page.get_text("text")
            cleaned = self.clean_text(raw_text)
            char_len = len(cleaned)
            total_characters += char_len

            if cleaned:
                pages_content.append({
                    "page_number": page_num,
                    "text": cleaned,
                    "char_count": char_len
                })

        doc.close()

        if total_characters == 0 or not pages_content:
            raise ValueError(
                f"No selectable text could be extracted from '{original_filename}'. "
                "The PDF might contain scanned images or lacks an OCR text layer. "
                "Please upload a text-selectable PDF."
            )

        # Chunk the extracted pages while preserving page citations
        chunks = self._chunk_pages(pages_content, doc_id, original_filename)

        metadata = {
            "id": doc_id,
            "filename": original_filename,
            "file_size": file_size_bytes,
            "file_size_formatted": self._format_size(file_size_bytes),
            "total_pages": total_pages,
            "text_pages": len(pages_content),
            "total_characters": total_characters,
            "total_chunks": len(chunks),
            "uploaded_at": datetime.utcnow().isoformat() + "Z"
        }

        return metadata, chunks

    def _chunk_pages(self, pages: List[Dict[str, Any]], doc_id: str, filename: str) -> List[Dict[str, Any]]:
        """
        Splits pages into overlapping chunks while binding each chunk to its source page.
        """
        all_chunks = []
        global_chunk_idx = 0

        for page_item in pages:
            page_num = page_item["page_number"]
            page_text = page_item["text"]

            page_chunks = self._split_text_with_overlap(page_text)
            for idx_on_page, chunk_text in enumerate(page_chunks):
                chunk_id = f"{doc_id}_p{page_num}_c{idx_on_page}"
                all_chunks.append({
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "filename": filename,
                    "page_number": page_num,
                    "chunk_index": global_chunk_idx,
                    "text": chunk_text,
                    "char_count": len(chunk_text)
                })
                global_chunk_idx += 1

        return all_chunks

    def _split_text_with_overlap(self, text: str) -> List[str]:
        """
        Splits text into chunks of roughly chunk_size characters with chunk_overlap.
        Attempts to break at paragraph breaks, then sentence boundaries, then words.
        """
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + self.chunk_size
            if end >= text_len:
                chunk = text[start:].strip()
                if chunk:
                    chunks.append(chunk)
                break

            # Try to break cleanly at paragraph break (\n\n)
            split_point = text.rfind('\n\n', start, end)
            if split_point == -1 or split_point <= start + (self.chunk_size // 3):
                # Try to break at sentence boundary (. ! ?)
                sentence_match = re.search(r'[.!?]\s+', text[start + (self.chunk_size // 3):end])
                if sentence_match:
                    split_point = start + (self.chunk_size // 3) + sentence_match.end()
                else:
                    # Try to break at whitespace
                    split_point = text.rfind(' ', start, end)
                    if split_point == -1 or split_point <= start:
                        split_point = end

            chunk = text[start:split_point].strip()
            if chunk:
                chunks.append(chunk)

            # Move start forward with overlap
            next_start = split_point - self.chunk_overlap
            if next_start <= start:
                next_start = split_point
            start = next_start

        return chunks

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Returns human-readable file size."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
