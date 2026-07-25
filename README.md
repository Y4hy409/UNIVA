# UNIVA — Privacy-Centric, Local-First AI Business Copilot

UNIVA is a secure, privacy-centric, on-premises AI Business Intelligence platform designed for MSMEs (Micro, Small, and Medium Enterprises). It integrates structured financial data (e.g., from TallyPrime ledgers) and unstructured company documents (e.g., SOPs, policies) into one unified offline copilot interface.

## 🚀 Key Features

* **Fast Intent Routing**: Deterministic classification rules route queries (like greetings or navigation actions) instantly without invoking the LLM, reducing latency on low-end hardware.
* **Natural Language to SQL**: Translates natural language business questions into safe, read-only SQL queries executed locally against a DuckDB database.
* **Document Intelligence & RAG**: Context-aware semantic document search using a local ChromaDB vector store.
* **Hybrid Data Path**: Simultaneously merges structured records and unstructured policies to answer complex business questions.
* **Model Agnostic Abstraction**: Abstracted LLM client wrappers allowing easy replacement of the local model (`qwen3:4b` / Ollama).
* **Apache ECharts Visualization**: Automatically structures and renders beautiful, responsive charts based on query metrics.

---

## 🛠️ Tech Stack

* **Frontend**: React (TypeScript), Vite, TailwindCSS (for custom modules), Lucide icons, Apache ECharts.
* **Backend**: FastAPI (Python 3.13), Uvicorn server.
* **Database**: DuckDB (Structured analytic transactional database), ChromaDB (Vector store).
* **AI Engine**: Ollama hosting local `qwen3:4b` instruct model.

---

## 💻 Getting Started

### Prerequisites
* Python 3.11+
* Node.js v18+
* [Ollama](https://ollama.com/) (installed and running locally)

---

### Step 1: Run the Ollama Model
Pull and run the default model in your terminal:
```bash
ollama run qwen3:4b
```

---

### Step 2: Set Up and Run the Backend API Sidecar
1. Navigate to the `backend` folder:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the server:
   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

---

### Step 3: Set Up and Run the Frontend Interface
1. Open a new terminal window and navigate to the `frontend` folder:
   ```bash
   cd frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Start the dev server:
   ```bash
   npm run dev
   ```
4. Open your browser and navigate to **`http://localhost:5173`**.

---

## 🧪 Running Tests

A comprehensive test suite of **54 unit and integration tests** validates SQL security, licensing, file sandboxing, intent routing, and memory context.

To run the backend tests:
```bash
cd backend
.\venv\Scripts\activate
python run_tests.py
```

To run only the Fast Intent Router test suite:
```bash
python -m unittest test_intent_router.py
```
