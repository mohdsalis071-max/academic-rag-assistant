# ScholarRAG – Intelligent AI Academic Assistant

ScholarRAG is a modern, high-performance, full-stack **Retrieval-Augmented Generation (RAG)** web application designed for students and educators. It transforms lecture slides, course notes, syllabi, and textbooks (PDFs) into an interactive, curriculum-grounded academic tutor powered by **Google Gemini AI**.

---

## 🌟 Key Features

- **Document Grounding & Retrieval**: Extracts, cleans, and chunks PDF materials while preserving precise **page numbers** and **source file references**.
- **Vector Search Engine**: High-speed, normalized cosine similarity retrieval over embeddings generated with Google's `text-embedding-004`.
- **Specialized Academic Study Modes**:
  - 💡 **General Academic Q&A**: In-depth theoretical and conceptual explanation.
  - 📝 **Document Summary**: Core themes, theorems, and key takeaways.
  - 🌱 **Explain Simply (ELI5)**: Intuitive real-world analogies without confusing jargon.
  - 🎯 **Exam-Oriented Prep**: Structured 10-mark university exam format (Definition, Key Points, Technical Analysis, Conclusion).
  - ⚡ **Revision Notes**: High-yield bullet points, formulas, and common pitfalls to avoid.
  - ❓ **Practice Questions & Quiz**: Formative short/analytical questions with model answers.
- **Strict Grounding & Citation**: Every document-based answer provides expandable source citations including PDF filename, page number, and text excerpt.
- **Out-of-Context Fallback**: When questions fall outside uploaded materials, ScholarRAG clearly flags the answer as general knowledge rather than making up false citations.
- **Modern UI/UX**:
  - Dark & Light theme with persistent localStorage state.
  - Markdown, syntax-highlighted code blocks (`highlight.js`), and LaTeX math formula rendering (`KaTeX`).
  - Drag-and-drop multiple PDF uploads with progress indicators.
  - Document filter to query across all materials or narrow down to a single PDF.
  - Dynamic API key configuration modal directly in the browser.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | Python 3.11+, FastAPI, Starlette |
| **Server Engine** | Uvicorn ASGI Server |
| **AI LLM** | Google Gemini (`gemini-2.5-flash` / `gemini-1.5-flash`) |
| **Embeddings** | Google GenAI SDK (`text-embedding-004`, 768 dimensions) |
| **Document Processing** | PyMuPDF (`fitz`) for high-speed page-aware PDF extraction |
| **Vector Search** | Vectorized Cosine Similarity (NumPy / FAISS-compatible) |
| **Frontend** | HTML5, CSS3, Vanilla ES6+ JavaScript, KaTeX, Marked.js, Highlight.js |
| **Cloud Deployment** | Render Web Service (Free Tier Ready) |
| **Version Control** | Git & GitHub |

---

## 📂 Project Structure

```text
academic-rag-assistant/
│
├── app.py                     # FastAPI application, REST endpoints, and lifecycle
├── rag_engine.py              # Embedding generation, vector storage, cosine search, and Gemini prompts
├── document_processor.py      # PyMuPDF page-by-page extraction, cleaning, and smart chunking
├── requirements.txt           # Production Python dependencies
├── runtime.txt                # Python runtime definition for Render (python-3.11.9)
├── render.yaml                # Render Blueprint deployment specification
├── .env.example               # Template for environment variables
├── .gitignore                 # Excludes cache, virtual environment, and local uploads
├── README.md                  # Comprehensive documentation and deployment guide
│
├── templates/
│   └── index.html             # Single-page application HTML interface
│
├── static/
│   ├── css/
│   │   └── style.css          # Responsive design, dark/light themes, typography
│   ├── js/
│   │   └── app.js             # Client state, drag-and-drop, API integration, rendering
│   └── favicon.svg            # Academic graduation cap brand favicon
│
├── uploads/                   # Temporary directory for uploaded files (.gitkeep)
└── storage/                   # Persistent/cached metadata and vector index (.gitkeep)
```

---

## 🚀 Local Setup on Windows

### 1. Prerequisites
- Python 3.10+ installed on your system.
- A free Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/app/apikey).

### 2. Open PowerShell in Project Directory
```powershell
cd C:\Users\LENOVO\.gemini\antigravity\scratch\academic-rag-assistant
```

### 3. Create and Activate Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 4. Install Dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure Your Gemini API Key
Create a `.env` file in the project root:
```powershell
Copy-Item .env.example .env
```
Open `.env` in any text editor and insert your key:
```env
GEMINI_API_KEY=AIzaSyYourActualKeyHere
PORT=8000
```
*(Alternatively, you can start the application and enter the key using the 🔑 icon directly in the web browser!)*

### 6. Run the Application
```powershell
python app.py
```
Or with Uvicorn:
```powershell
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

## 🧪 Testing the RAG Pipeline Locally

1. **Verify Health Endpoint**:
   Visit `http://127.0.0.1:8000/health` to confirm the server status is `"healthy"`.
2. **Upload a Sample PDF**:
   - Drag and drop any lecture note or course syllabus PDF into the left sidebar dropzone.
   - Watch the indicator change from `Processing...` to `Uploaded X pages, Y chunks`.
3. **Ask an Academic Question**:
   - Select a study mode (e.g., **Exam Prep** or **Summarize Notes**).
   - Type a question relevant to your uploaded material (e.g., *"What are the primary theorems discussed on page 1?"*).
   - Verify that ScholarRAG displays the answer with a green **"Document Grounded"** badge and an expandable **"Verified Source Citations"** section citing the exact filename and page number!
4. **Test Out-of-Scope Behavior**:
   - Ask an unrelated question (e.g., *"Who was the Roman emperor in 44 BC?"* when you uploaded a computer science PDF).
   - Verify that ScholarRAG clearly indicates that the topic was not found in the uploaded documents and labels the answer as general knowledge.

---

## ☁️ Free Deployment on Render via GitHub

ScholarRAG is configured to deploy directly to **Render** using a free **Web Service**.

### Step 1: Push Project to GitHub
1. Create a new repository on [GitHub](https://github.com) named `academic-rag-assistant`.
2. Initialize git and push your files:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of ScholarRAG application"
   git branch -M main
   git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/academic-rag-assistant.git
   git push -u origin main
   ```

### Step 2: Create Web Service on Render
1. Log in to [Render](https://render.com).
2. Click **New +** > **Web Service**.
3. Choose **Build and deploy from a Git repository** and connect your `academic-rag-assistant` repo.

### Step 3: Configure Settings in Render
Fill in the following fields:

- **Name**: `scholar-rag` (or your chosen name)
- **Region**: Choose the closest region (e.g., *Oregon (US West)* or *Frankfurt (EU)*)
- **Branch**: `main`
- **Root Directory**: Leave blank (root of repository)
- **Runtime**: `Python 3`
- **Build Command**:
  ```bash
  pip install --upgrade pip && pip install -r requirements.txt
  ```
- **Start Command**:
  ```bash
  uvicorn app:app --host 0.0.0.0 --port $PORT
  ```
- **Instance Type**: `Free`

### Step 4: Add Environment Variables
Under the **Environment Variables** section on Render, add:

| Key | Value | Notes |
|---|---|---|
| `GEMINI_API_KEY` | `AIzaSy...` | Your Google Gemini API key |
| `PYTHON_VERSION` | `3.11.9` | Ensures exact Python runtime compatibility |

### Step 5: Deploy
Click **Create Web Service**. Render will:
1. Clone your GitHub repository.
2. Install dependencies from `requirements.txt`.
3. Launch Uvicorn listening on Render's dynamic `$PORT`.
4. Provide a free public HTTPS URL: `https://scholar-rag.onrender.com`.

---

## ⚠️ Note on Render Free Tier Ephemeral Storage

> [!NOTE]
> Render's Free Web Services utilize **ephemeral filesystem storage**. This means:
> - Any uploaded PDFs or local vector caches created during a session are stored in temporary container memory.
> - When the free instance enters sleep mode after 15 minutes of inactivity or when a new deployment is triggered, the filesystem is refreshed.
> - **Built-in Resiliency**: ScholarRAG is designed specifically to handle this limitation gracefully. The interface provides clear upload indicators and document management, allowing users to re-upload notes in seconds or supply their API key on demand.

---

## 🔒 Security Best Practices

- **Zero Key Leaks**: The `GEMINI_API_KEY` is strictly processed on the server backend and is never exposed in client HTML or JavaScript.
- **File Validation**: Strict PDF MIME/extension verification and 25 MB payload limits protect the application from memory overflows.
- **Input Sanitization**: Client queries and document text are stripped of control characters before embedding and prompt injection.
