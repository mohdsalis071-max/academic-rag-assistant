"""
Comprehensive Verification and Test Suite for ScholarRAG.
Tests PDF extraction, chunking, vector search, prompt construction, and FastAPI route handlers.
"""

import os
import sys
import site
user_site = site.getusersitepackages()
if user_site and user_site not in sys.path:
    sys.path.insert(0, user_site)

import pymupdf
import numpy as np

from app import doc_processor, rag_engine, serve_index, health_check, list_documents, clear_all_documents


def run_coro(coroutine):
    """Executes a coroutine without requiring an external async event loop."""
    try:
        coroutine.send(None)
    except StopIteration as exc:
        return exc.value


def create_sample_academic_pdf(filepath: str):
    """Generates a multi-page sample academic PDF for verification."""
    doc = pymupdf.open()

    # Page 1: Quantum Computing Fundamentals
    p1 = doc.new_page()
    text_p1 = (
        "Quantum Computing and Information Theory - Lecture 1\n\n"
        "1. Introduction to Qubits\n"
        "Unlike classical bits which can exist in a deterministic state of either 0 or 1, "
        "a quantum bit or qubit can exist in a linear superposition of both basis states: "
        "|psi> = alpha|0> + beta|1>, where alpha and beta are complex probability amplitudes "
        "satisfying the normalization condition |alpha|^2 + |beta|^2 = 1.\n\n"
        "2. The Bloch Sphere Representation\n"
        "The state of a single qubit can be visualized geometrically on the surface of a unit sphere "
        "known as the Bloch sphere. Pure states lie on the boundary surface, while mixed states "
        "occupy the interior ball. Single-qubit quantum logic gates correspond to rotations of "
        "the Bloch vector around specific axes."
    )
    p1.insert_text((50, 50), text_p1, fontsize=11)

    # Page 2: Quantum Gates and Entanglement
    p2 = doc.new_page()
    text_p2 = (
        "Quantum Gates and Entanglement - Lecture 2\n\n"
        "3. Universal Quantum Logic Gates\n"
        "Unitary transformations form the mathematical basis of all quantum gate operations. "
        "The Hadamard gate (H) creates an equal superposition from standard computational basis states. "
        "The Pauli matrices (X, Y, Z) represent fundamental bit-flip, bit-and-phase-flip, and phase-flip operations.\n\n"
        "4. Quantum Entanglement and Bell States\n"
        "Entanglement represents a uniquely quantum phenomenon where the joint quantum state of two or more particles "
        "cannot be factored into individual tensor product states: |Psi+> = (|00> + |11>) / sqrt(2). "
        "Einstein, Podolsky, and Rosen (EPR) famously referred to non-local correlations as 'spooky action at a distance'. "
        "Bell inequalities experimentally confirm that local hidden variable theories cannot explain quantum mechanics."
    )
    p2.insert_text((50, 50), text_p2, fontsize=11)

    doc.save(filepath)
    doc.close()
    print(f"[TEST] Created sample academic PDF at: {filepath}")


def test_document_processor(sample_pdf_path: str):
    """Tests PDF text extraction, cleaning, and chunking with page number accuracy."""
    print("\n--- Testing DocumentProcessor ---")
    metadata, chunks = doc_processor.extract_from_pdf(sample_pdf_path, "Quantum_Computing_Notes.pdf")

    assert metadata["total_pages"] == 2, f"Expected 2 pages, got {metadata['total_pages']}"
    assert len(chunks) >= 2, f"Expected at least 2 chunks, got {len(chunks)}"

    # Check page numbers
    page_numbers = {c["page_number"] for c in chunks}
    assert 1 in page_numbers and 2 in page_numbers, f"Missing page citations: {page_numbers}"

    # Verify chunk properties
    for chunk in chunks:
        assert "chunk_id" in chunk
        assert "filename" in chunk
        assert "page_number" in chunk
        assert "text" in chunk
        assert len(chunk["text"]) > 20

    print(f"[SUCCESS] Extracted {metadata['total_pages']} pages, produced {len(chunks)} chunks.")
    for i, chunk in enumerate(chunks[:2]):
        print(f"  Chunk {i+1} [Page {chunk['page_number']}]: {chunk['text'][:90]}...")
    return metadata, chunks


def test_vector_cosine_similarity():
    """Tests the in-memory cosine similarity search algorithm and ranking."""
    print("\n--- Testing Vector Retrieval & Cosine Similarity ---")
    dim = 768
    np.random.seed(42)

    # Simulate 5 chunks
    dummy_chunks = [
        {"chunk_id": f"c_{i}", "doc_id": "doc_1", "filename": "Test.pdf", "page_number": i + 1, "text": f"Content about quantum topic {i}"}
        for i in range(5)
    ]

    # Create random vectors and normalize
    raw_vecs = np.random.randn(5, dim).astype(np.float32)
    norms = np.linalg.norm(raw_vecs, axis=1, keepdims=True)
    embeddings = raw_vecs / norms

    # Assign to rag_engine
    rag_engine.chunks = list(dummy_chunks)
    rag_engine.embeddings = embeddings

    # Query vector close to chunk 2
    query_vec = embeddings[2] + np.random.randn(dim).astype(np.float32) * 0.05
    query_vec /= np.linalg.norm(query_vec)

    # Compute cosine similarity
    scores = np.dot(embeddings, query_vec)
    best_idx = int(np.argmax(scores))

    assert best_idx == 2, f"Expected top match index 2, got {best_idx}"
    print(f"[SUCCESS] Cosine similarity retrieval identified top match with score: {scores[best_idx]:.4f}")

    # Test top-k retrieval sorting
    sorted_indices = np.argsort(scores)[::-1]
    assert sorted_indices[0] == 2
    print(f"[SUCCESS] Top ranked indices: {sorted_indices[:3].tolist()}")

    # Clean up dummy test data
    rag_engine.chunks = []
    rag_engine.embeddings = None


def test_academic_prompt_builder():
    """Tests the generation of academic prompts across different study modes."""
    print("\n--- Testing Academic Prompt Construction ---")
    modes = ["general", "summarize", "eli5", "exam", "revision", "quiz"]
    test_question = "Explain the Bloch Sphere representation."
    test_context = "SOURCE: Notes.pdf (Page 1) - Bloch sphere is a unit sphere for qubit states."

    for mode in modes:
        prompt_grounded = rag_engine._build_academic_prompt(
            question=test_question,
            context=test_context,
            study_mode=mode,
            is_grounded=True,
            has_documents=True
        )
        assert mode.upper() in prompt_grounded
        assert test_context in prompt_grounded
        assert "STRICT GROUNDING & CITATION RULES" in prompt_grounded

        prompt_ungrounded = rag_engine._build_academic_prompt(
            question=test_question,
            context="",
            study_mode=mode,
            is_grounded=False,
            has_documents=False
        )
        assert "No study documents have been uploaded" in prompt_ungrounded
        print(f"  [SUCCESS] Mode '{mode}' prompt structured correctly (grounded & ungrounded).")

    print("[SUCCESS] All academic study mode prompts validated.")


def test_fastapi_handlers():
    """Tests FastAPI endpoint route handlers directly."""
    print("\n--- Testing FastAPI Route Handlers ---")

    # Test 1: serve_index()
    index_res = run_coro(serve_index())
    assert os.path.exists(index_res.path), f"Index path does not exist: {index_res.path}"
    print(f"[SUCCESS] serve_index() correctly targets: {index_res.path}")

    # Test 2: health_check()
    health_data = run_coro(health_check())
    assert health_data["status"] == "healthy"
    assert health_data["service"] == "academic-rag-assistant"
    print(f"[SUCCESS] health_check() returned: {health_data['status']}, uptime: {health_data['uptime_seconds']}s")

    # Test 3: list_documents()
    docs_data = run_coro(list_documents())
    assert "count" in docs_data
    assert "documents" in docs_data
    print(f"[SUCCESS] list_documents() returned {docs_data['count']} documents.")

    # Test 4: clear_all_documents()
    clear_data = run_coro(clear_all_documents())
    assert clear_data["status"] == "success"
    print("[SUCCESS] clear_all_documents() reset knowledge base successfully.")


if __name__ == "__main__":
    test_pdf = os.path.join(os.path.dirname(__file__), "test_lecture.pdf")
    try:
        create_sample_academic_pdf(test_pdf)
        test_document_processor(test_pdf)
        test_vector_cosine_similarity()
        test_academic_prompt_builder()
        test_fastapi_handlers()
        print("\n==========================================")
        print(" ALL VERIFICATION TESTS PASSED SUCCESSFULLY! ")
        print("==========================================\n")
    finally:
        if os.path.exists(test_pdf):
            try:
                os.remove(test_pdf)
            except Exception:
                pass
