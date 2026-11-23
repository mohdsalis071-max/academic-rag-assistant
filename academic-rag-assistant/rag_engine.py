"""
RAG Engine Module for Academic Assistant.
Handles embedding generation, in-memory vector storage, cosine similarity search,
and Gemini AI prompt construction for academic inquiry.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

# Ensure local site packages are available
import site
import sys
user_site = site.getusersitepackages()
if user_site and user_site not in sys.path:
    sys.path.insert(0, user_site)

from google import genai
from google.genai import types
from google.genai.errors import APIError

logger = logging.getLogger("rag_engine")
logger.setLevel(logging.INFO)


class RAGEngine:
    def __init__(self, storage_dir: str = "storage", api_key: Optional[str] = None):
        """
        Initialize the RAG Engine.
        :param storage_dir: Directory where vector data and document metadata are stored.
        :param api_key: Gemini API Key (optional, will check environment variable GEMINI_API_KEY).
        """
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

        self.docs_file = os.path.join(self.storage_dir, "documents.json")
        self.chunks_file = os.path.join(self.storage_dir, "chunks.json")
        self.vectors_file = os.path.join(self.storage_dir, "embeddings.npy")

        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
        self.embedding_model = "text-embedding-004"
        self.generation_model = "gemini-3.8-flash"
        self.fallback_generation_model = "gemini-2.5-flash"

        # In-memory storage for lightning-fast retrieval
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.chunks: List[Dict[str, Any]] = []
        self.embeddings: Optional[np.ndarray] = None

        self._client: Optional[genai.Client] = None
        self._init_client()
        self._load_storage()

    def _init_client(self):
        """Initializes the Google GenAI client if an API key is available."""
        if self.api_key:
            try:
                self._client = genai.Client(api_key=self.api_key)
                logger.info("Google GenAI client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize GenAI client: {e}")
                self._client = None
        else:
            self._client = None
            logger.warning("No GEMINI_API_KEY found. RAG generation will require user-provided key.")

    def set_api_key(self, api_key: str):
        """Updates the Gemini API key dynamically."""
        if api_key and api_key.strip():
            self.api_key = api_key.strip()
            self._init_client()

    def is_configured(self) -> bool:
        """Returns True if the Gemini API key is configured."""
        return bool(self.api_key and self._client)

    def _load_storage(self):
        """Loads documents, chunks, and embeddings from disk if present."""
        try:
            if os.path.exists(self.docs_file):
                with open(self.docs_file, "r", encoding="utf-8") as f:
                    self.documents = json.load(f)
            else:
                self.documents = {}

            if os.path.exists(self.chunks_file):
                with open(self.chunks_file, "r", encoding="utf-8") as f:
                    self.chunks = json.load(f)
            else:
                self.chunks = []

            if os.path.exists(self.vectors_file):
                self.embeddings = np.load(self.vectors_file)
                # Verify shape alignment
                if len(self.chunks) != self.embeddings.shape[0]:
                    logger.warning("Chunk count mismatch with embeddings. Resetting vector cache.")
                    self.embeddings = None
            else:
                self.embeddings = None

            logger.info(f"Loaded {len(self.documents)} documents, {len(self.chunks)} chunks into RAG engine.")
        except Exception as e:
            logger.error(f"Error loading RAG storage: {e}. Starting fresh.")
            self.documents = {}
            self.chunks = []
            self.embeddings = None

    def _save_storage(self):
        """Persists documents, chunks, and embeddings to disk."""
        try:
            with open(self.docs_file, "w", encoding="utf-8") as f:
                json.dump(self.documents, f, indent=2, ensure_ascii=False)

            with open(self.chunks_file, "w", encoding="utf-8") as f:
                json.dump(self.chunks, f, indent=2, ensure_ascii=False)

            if self.embeddings is not None and len(self.embeddings) > 0:
                np.save(self.vectors_file, self.embeddings)
            elif os.path.exists(self.vectors_file):
                os.remove(self.vectors_file)
        except Exception as e:
            logger.error(f"Error saving RAG storage: {e}")

    def get_embeddings(self, texts: List[str], batch_size: int = 30) -> np.ndarray:
        """
        Computes text embeddings using Google's text-embedding-004 model.
        Returns a normalized 2D numpy array of embeddings (N, D).
        """
        if not self._client:
            raise ValueError(
                "Gemini API key is not configured. Please set the GEMINI_API_KEY environment variable or provide it in the UI."
            )

        if not texts:
            return np.empty((0, 768), dtype=np.float32)

        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            try:
                response = self._client.models.embed_content(
                    model=self.embedding_model,
                    contents=batch,
                )
                for item in response.embeddings:
                    all_embeddings.append(item.values)
            except Exception as e:
                logger.error(f"Error generating embeddings for batch {i}: {e}")
                raise RuntimeError(f"Google Gemini Embedding API error: {str(e)}")

        arr = np.array(all_embeddings, dtype=np.float32)
        # Normalize vectors for cosine similarity (dot product = cosine similarity)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10
        return arr / norms

    def add_document(self, metadata: Dict[str, Any], chunks: List[Dict[str, Any]]):
        """
        Embeds document chunks and saves the document to the vector store.
        """
        if not chunks:
            return

        texts = [c["text"] for c in chunks]
        logger.info(f"Embedding {len(texts)} chunks for document '{metadata.get('filename')}'...")
        new_embeddings = self.get_embeddings(texts)

        # Update in-memory state
        doc_id = metadata["id"]
        self.documents[doc_id] = metadata
        self.chunks.extend(chunks)

        if self.embeddings is None or len(self.embeddings) == 0:
            self.embeddings = new_embeddings
        else:
            self.embeddings = np.vstack([self.embeddings, new_embeddings])

        self._save_storage()
        logger.info(f"Document {doc_id} ('{metadata.get('filename')}') added successfully.")

    def delete_document(self, doc_id: str) -> bool:
        """
        Deletes a document and its associated chunks and embeddings.
        """
        if doc_id not in self.documents:
            return False

        indices_to_keep = [i for i, c in enumerate(self.chunks) if c["doc_id"] != doc_id]

        self.chunks = [self.chunks[i] for i in indices_to_keep]
        del self.documents[doc_id]

        if len(indices_to_keep) > 0 and self.embeddings is not None:
            self.embeddings = self.embeddings[indices_to_keep]
        else:
            self.embeddings = None

        self._save_storage()
        logger.info(f"Document {doc_id} removed from RAG index.")
        return True

    def clear_all(self):
        """Clears all documents and vector indices."""
        self.documents.clear()
        self.chunks.clear()
        self.embeddings = None
        self._save_storage()
        logger.info("Cleared all documents from RAG index.")

    def retrieve(self, query: str, top_k: int = 5, doc_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves the top_k most relevant chunks for a student query using cosine similarity.
        :param query: The student's question.
        :param top_k: Number of chunks to retrieve.
        :param doc_id: Optional document ID filter.
        :return: List of retrieved chunks with similarity scores.
        """
        if not self.chunks or self.embeddings is None or len(self.embeddings) == 0:
            return []

        # Generate normalized embedding for query
        query_emb = self.get_embeddings([query])  # shape: (1, D)
        query_vec = query_emb[0]

        # Calculate cosine similarity
        scores = np.dot(self.embeddings, query_vec)

        # Filter by doc_id if specified
        if doc_id:
            filtered_indices = [i for i, c in enumerate(self.chunks) if c["doc_id"] == doc_id]
        else:
            filtered_indices = list(range(len(self.chunks)))

        if not filtered_indices:
            return []

        # Sort filtered indices by score descending
        sorted_indices = sorted(filtered_indices, key=lambda idx: scores[idx], reverse=True)
        top_indices = sorted_indices[:top_k]

        results = []
        for idx in top_indices:
            chunk = dict(self.chunks[idx])
            chunk["score"] = float(scores[idx])
            results.append(chunk)

        return results

    def generate_academic_response(
        self,
        question: str,
        study_mode: str = "general",
        doc_id: Optional[str] = None,
        top_k: int = 5,
        relevance_threshold: float = 0.40
    ) -> Dict[str, Any]:
        """
        Executes the RAG pipeline:
        1. Retrieves relevant chunks.
        2. Evaluates context relevance against threshold.
        3. Formulates academic prompt for Gemini.
        4. Generates structured academic response with source citations.
        """
        if not self._client:
            raise ValueError(
                "Gemini API key is not configured. Please set the GEMINI_API_KEY environment variable or provide it in the UI."
            )

        # Step 1: Retrieve relevant chunks
        has_documents = len(self.chunks) > 0
        retrieved_chunks = self.retrieve(question, top_k=top_k, doc_id=doc_id) if has_documents else []

        # Check top relevance score
        top_score = retrieved_chunks[0]["score"] if retrieved_chunks else 0.0
        is_grounded = bool(retrieved_chunks and top_score >= relevance_threshold)

        # Build context from chunks
        context_blocks = []
        citations = []
        seen_citations = set()

        if is_grounded:
            for c in retrieved_chunks:
                # Include chunks that are relevant (>= threshold or close to top score)
                if c["score"] >= max(relevance_threshold, top_score - 0.25):
                    context_blocks.append(
                        f"--- SOURCE: {c['filename']} (Page {c['page_number']}) ---\n{c['text']}"
                    )
                    cite_key = (c["filename"], c["page_number"])
                    if cite_key not in seen_citations:
                        seen_citations.add(cite_key)
                        citations.append({
                            "document": c["filename"],
                            "page": c["page_number"],
                            "score": round(c["score"], 3),
                            "preview": c["text"][:180] + ("..." if len(c["text"]) > 180 else "")
                        })

        context_text = "\n\n".join(context_blocks)

        # Step 2: Build the prompt according to academic study mode
        prompt = self._build_academic_prompt(
            question=question,
            context=context_text,
            study_mode=study_mode,
            is_grounded=is_grounded,
            has_documents=has_documents
        )

        # Step 3: Call Gemini
        answer = self._call_gemini(prompt)

        return {
            "answer": answer,
            "grounded": is_grounded,
            "study_mode": study_mode,
            "citations": citations,
            "top_score": round(top_score, 3) if top_score else 0.0,
            "chunks_retrieved": len(retrieved_chunks)
        }

    def _build_academic_prompt(
        self,
        question: str,
        context: str,
        study_mode: str,
        is_grounded: bool,
        has_documents: bool
    ) -> str:
        """
        Creates tailored academic prompts based on study modes and document context availability.
        """
        mode_instructions = {
            "general": (
                "Provide a rigorous, clear, and comprehensive academic explanation. "
                "Break down complex terminology, give illustrative examples, and use structured markdown headings, lists, or tables."
            ),
            "summarize": (
                "Provide a high-yield academic summary. Include: "
                "1. Core Objective/Theme, 2. Key Definitions & Concepts, 3. Essential Formulas or Theories (if applicable), "
                "and 4. Critical Takeaways for students."
            ),
            "eli5": (
                "Explain the topic in simple, intuitive language as if teaching a beginner (ELI5). "
                "Use a clear real-world analogy, step-by-step breakdown, and avoid dense jargon without defining it first."
            ),
            "exam": (
                "Format this answer specifically for high-scoring university/college examinations. Include: "
                "- Standard Formal Definition\n"
                "- Core Principles / Key Points (bulleted)\n"
                "- Detailed Technical Explanation\n"
                "- Important Edge Cases or Examples\n"
                "- Model Exam Conclusion or Diagrammatic description."
            ),
            "revision": (
                "Generate concise, high-impact revision notes. Use bullet points, bold key terms, "
                "highlight formulas, and add a 'Common Pitfalls / Mistakes to Avoid' section."
            ),
            "quiz": (
                "Generate 5 exam-oriented practice questions based on this topic: "
                "2 Conceptual/Short-Answer questions, 2 In-Depth Analytical questions, and 1 Application/Problem-Solving scenario. "
                "Provide detailed model answers and grading rubrics for each."
            )
        }

        mode_guidance = mode_instructions.get(study_mode, mode_instructions["general"])

        if is_grounded:
            prompt = f"""You are an elite, encouraging AI Academic Professor and Tutor assisting university and high-school students.

STUDY MODE: {study_mode.upper()}
SPECIAL INSTRUCTION: {mode_guidance}

RETRIEVED ACADEMIC DOCUMENTS CONTEXT:
\"\"\"
{context}
\"\"\"

STUDENT QUESTION / REQUEST:
\"\"\"{question}\"\"\"

STRICT GROUNDING & CITATION RULES:
1. Base your explanation primarily on the retrieved academic context provided above.
2. Whenever referencing a specific fact, formula, theorem, or finding, explicitly cite the source document name and page number in brackets (e.g. `[Document_Name.pdf, Page X]`).
3. If the retrieved context covers only part of the student's question, answer the covered portion from the materials first, and then supplement with standard academic knowledge while clearly stating that the supplementary part is general academic knowledge.
4. Format your answer with beautiful, readable GitHub Markdown: use bolding for key terms, clear headers (###), bullet points, and code blocks or LaTeX-style math formulas (e.g. `$E = mc^2$`) where appropriate.
"""
        else:
            if not has_documents:
                status_note = (
                    "**Note:** No study documents have been uploaded to your session yet. "
                    "The answer below is provided from general academic knowledge. "
                    "Upload your course lecture PDFs, syllabus, or notes to get exact curriculum-grounded answers!"
                )
            else:
                status_note = (
                    "**Note:** The uploaded academic materials in your session do not appear to contain relevant information "
                    "to answer this specific question. The answer below is provided from general academic knowledge."
                )

            prompt = f"""You are an elite, encouraging AI Academic Professor and Tutor.

STUDY MODE: {study_mode.upper()}
SPECIAL INSTRUCTION: {mode_guidance}

STUDENT QUESTION / REQUEST:
\"\"\"{question}\"\"\"

DOCUMENT STATUS:
{status_note}

INSTRUCTIONS:
1. Begin your response with the following exact disclaimer block:
> ⚠️ {status_note}

2. Then provide an exceptionally thorough, accurate, and structured academic answer based on general academic knowledge.
3. Use clear markdown headers, bullet points, intuitive explanations, and examples.
"""
        return prompt

    def _call_gemini(self, prompt: str) -> str:
        """
        Sends the prompt to Gemini with automatic model fallback and error handling.
        """
        # Try primary model first, fallback to secondary if quota/availability issue
        models_to_try = [self.generation_model, self.fallback_generation_model, "gemini-2.5-flash"]
        last_error = None

        for model_name in models_to_try:
            try:
                response = self._client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.3,  # Academic precision
                        max_output_tokens=3000,
                    )
                )
                if response and response.text:
                    return response.text
                elif response and hasattr(response, "candidates") and response.candidates:
                    first_cand = response.candidates[0]
                    if hasattr(first_cand, "content") and first_cand.content and first_cand.content.parts:
                        return first_cand.content.parts[0].text
            except APIError as api_err:
                logger.warning(f"Gemini API error with model '{model_name}': {api_err}")
                last_error = api_err
                continue
            except Exception as e:
                logger.warning(f"Error calling Gemini model '{model_name}': {e}")
                last_error = e
                continue

        raise RuntimeError(f"Unable to generate response from Gemini API: {str(last_error)}")

    def get_stats(self) -> Dict[str, Any]:
        """Returns statistics about the current RAG knowledge base."""
        return {
            "total_documents": len(self.documents),
            "total_chunks": len(self.chunks),
            "total_pages": sum(d.get("total_pages", 0) for d in self.documents.values()),
            "api_key_configured": self.is_configured(),
            "embedding_model": self.embedding_model,
            "generation_model": self.generation_model
        }
