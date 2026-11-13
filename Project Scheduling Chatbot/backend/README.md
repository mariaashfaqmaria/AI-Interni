Project Scheduling Chatbot — Setup and Run
This is a separate application based on the supplied backend and frontend exports. The existing frontend design and the authentication, chat, history, planner, schedule, and task pages are retained.
Approved project catalogue
The application is configured for exactly 16 approved projects:
10 projects from `backend/data/AI_Project_Data.pdf`
6 starter projects from `backend/src/services/seed.py`
16 distinct domains
The PDF project titles/domains were verified from the supplied PDF. The database synchronizer removes unapproved/custom catalogue rows and clears user selections that point to removed rows. Existing plans, tasks, schedules, conversations, and messages are not deleted.
The six seed projects are:
Smart Factory Quality Control — Manufacturing
Personalized Travel Discovery Platform — Tourism
Athlete Performance Analysis System — Sports
Restaurant Operations Management System — Food Service
Digital Public Service Portal — Government
Renewable Energy Monitoring Dashboard — Energy
The ten PDF projects are:
PulsePath — Healthcare
SkillSpring — Education
LedgerLoop — Finance
FieldNest — Agriculture
CartCanvas — E-commerce
RouteRipple — Transportation
HavenKey — Real Estate
SceneSync — Entertainment
AccessHarbor — Cybersecurity
EcoTrace — Environment
1. Create the PostgreSQL database
In pgAdmin, create a new database named:
`project_scheduling_chatbot_db`
Do not use the database of the older application if you want this project to remain independent.
2. Configure the backend environment
Open PowerShell:
```powershell
cd "D:\AI_Interni(Projects)\Project Scheduling Chatbot\backend"
Copy-Item .env.example .env
```
Open `backend/.env` and fill in your own:
PostgreSQL password
OpenRouter API key
Pinecone API key
generated SECRET_KEY
Generate a new secret key:
```powershell
uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
```
Paste the generated output after `SECRET_KEY=` in `.env`.
Do not share `.env` or commit it to Git.
3. Install Python dependencies with uv
Python 3.12 is recommended:
```powershell
uv python install 3.12
uv python pin 3.12
uv sync
```
The project uses `pyproject.toml`; a `requirements.txt` file is not required.
If the dependencies are already installed in this backend environment, `uv sync` will check/reconcile them against `pyproject.toml`.
4. Pinecone configuration
The new application uses:
```env
PINECONE_INDEX=project-scheduling-chatbot
PINECONE_NAMESPACE=project-scheduling-data
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
```
The backend creates the index automatically if it does not exist. It checks the index dimension before ingestion.
On the first successful startup, it indexes 16 project documents into the new namespace. Re-ingestion uses stable IDs and removes stale IDs only inside this project's configured namespace. It does not delete or modify the old application's index.
Set `PINECONE_API_KEY` to enable Pinecone. If it is blank, the backend uses local PDF/seed retrieval instead.
The embedding model may need to download its model files the first time it runs.
5. Run the backend
Keep the terminal in the `backend` folder:
```powershell
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8001
```
Backend:
API: `http://127.0.0.1:8001`
Swagger: `http://127.0.0.1:8001/docs`
Health: `http://127.0.0.1:8001/health`
Check `/health`. With the PDF and Pinecone configured, expected values include:
`pdf_projects`: 10
`seed_projects`: 6
`expected_total_projects`: 16
`pinecone_vectors`: 16
6. Run the frontend
Open a second VS Code terminal:
```powershell
cd "D:\AI_Interni(Projects)\Project Scheduling Chatbot\frontend"
npm install
npm run dev
```
Open the Vite URL printed in the terminal, normally `http://localhost:5173`.
The Vite proxy points to backend port `8001`.
7. LangGraph behaviour
The chat graph uses separate routes:
Project details request → `get_project` → `generate_project_answer` → END
Explicit plan request → `get_project` → `generate_plan` → END
Other document/catalogue question → `retrieve_document` → `generate` → END
General advice mode → `general_advice` → `generate` → END
The plan node receives the exact project object selected by `get_project`; it does not independently guess a second project. A requested duration in days is used (bounded by the existing planner limit of 60 days). If no duration is specified, the project suggestion/default is used.
The PDF is factual grounding. The LLM may add practical implementation recommendations, but the prompt instructs it to label recommendations separately and not attribute them to the PDF.
8. Important notes
Do not copy the old `.venv` or `node_modules` into this project.
Keep this project's `.env`, PostgreSQL database, Pinecone index, and namespace separate from the older project.
The `/projects` custom-project creation endpoint has been removed. The API only lists/returns the approved catalogue.
The document upload route validates the uploaded PDF against the approved ten titles and domains before accepting it.
The backend can start in local retrieval mode if Pinecone is not configured. For the requested new Pinecone index, configure the Pinecone key.
The app can start without an OpenRouter key, but LLM-generated answers require `OPENROUTER_API_KEY`.
Validation performed on the supplied source
Python source files passed `compileall` syntax compilation.
The supplied PDF was parsed: 6 pages, exactly 10 numbered project headings.
The SQL catalogue smoke test created exactly 16 project rows and confirmed 16 unique domains.
Live PostgreSQL, Pinecone, OpenRouter, and browser integration tests still require your own credentials and local services; no code-only review can honestly guarantee zero runtime errors across those external services.