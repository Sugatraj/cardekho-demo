# 🚗 CarDekho Matchmaker: AI Used Car Finder & Shortlist Comparison

A modern, full-stack AI-native application designed to help used car buyers go from *"I don't know what to buy"* to *"I'm confident in my shortlist."* 

---

## 🔗 Deliverable Links
* **Live Deployment URL**: [Insert your Vercel deployment link here]
* **Screen Recording (Build Process)**: [Insert your Loom / Drive video link here]

---

## 📖 Project Documentation & Evaluation Questions

### 1. What did you build and why? What did you deliberately cut?
* **What was built**: We built a full-stack, single-command monorepo featuring a **React (Vite) frontend** styled with **Tailwind CSS** and a **FastAPI backend** running over a local **SQLite database** containing **15,411 used cars** (sourced from Kaggle). 
  * The core feature is a **Structured RAG (Text-to-SQL) Agent** powered by **Gemini 2.5 Flash**. Users express their needs in natural language, the AI translates the prompt into a precise SQLite query, executes it over 100% of the dataset, and then provides a conversational summary.
  * Users can click **Shortlist** on any match to add it to a side-by-side comparison drawer to evaluate specs (age, price, mileage, power) side-by-side.
* **Why**: Natural language search is the best way to handle complex buyer requirements (e.g., *"automatic petrol cars under 6 Lakhs with good mileage"*). Comparing them side-by-side solves final choice paralysis.
* **What was deliberately cut**:
  * **Vector Embeddings (Traditional RAG)**: Traditional vector search was cut because it is notoriously inaccurate with exact numbers (like budget caps or age limits). Text-to-SQL is the industry-standard way to query structured data.
  * **User Authentication**: Cut to keep the deployment simple and runnable in under 2 minutes.
  * **Persistent External Cloud Database**: Sourced as a local SQLite file so that the project requires zero database connection strings to run.

### 2. What’s your tech stack and why did you pick it?
* **Frontend**: React (Vite), Tailwind CSS, Lucide Icons.
  * *Why*: Fast, modern, responsive UI scaffolding. Vite ensures near-instant local server start times.
* **Backend**: Python (FastAPI), Uvicorn.
  * *Why*: FastAPI is extremely fast, automatically generates OpenAPI documentation, and runs natively as a serverless function on Vercel.
* **Database**: SQLite (built-in).
  * *Why*: Lightweight, file-based, requires no external background services, and is extremely fast for querying 15k+ records.
* **AI Provider**: Google GenAI SDK (Gemini 2.5 Flash).
  * *Why*: Extremely fast response times, native support for JSON structured outputs (essential for SQL generation), and a highly cost-effective free tier.

### 3. What did you delegate to AI tools vs. do manually? Where did the tools help most? Where did they get in the way?
* **Delegated to AI**:
  * Initial scaffolding for the Tailwind CSS dashboard layout.
  * Drafting the SQL generation prompts.
* **Done Manually**:
  * Python dependency conflict resolution (ensuring FastAPI, HTTPX, and OpenAI versions play nicely together).
  * Data parsing and type casting inside `db_importer.py` to ensure SQLite handles NULL entries gracefully.
* **Where AI helped most**:
  * Scaffolding the React components and icons very quickly, letting us focus on core backend engineering.
* **Where AI got in the way**:
  * Handling Python library deprecations. The AI initially suggested deprecated packages (`google-generativeai` and old `openai` versions) which had broken endpoints and version conflicts under Python 3.14. We had to manually debug these dependencies.

### 4. If you had another 4 hours, what would you add?
1. **Dynamic Sort and Filter**: Allow users to sort matches (e.g., sort by price/mileage) directly on the frontend dashboard without prompting the AI.
2. **Review Summarization**: Feed the `user_reviews` column from the database into Gemini to generate pros/cons lists for shortlisted cars.
3. **Saved Sessions**: Use browser localStorage or a lightweight Supabase integration to persist the user's shortlist between page reloads.

---

## ⚡ Local Setup & Run Instructions (Under 2 Minutes)

### Prerequisites
* Python 3.10+
* Node.js 18+

### Step 1: Install Dependencies
1. Install Python packages:
   ```bash
   pip install -r requirements.txt
   ```
2. Install Node packages:
   ```bash
   npm install
   ```

### Step 2: Configure Environment Variables
Create a `.env` file in the root directory and add your Google AI Studio API key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### Step 3: Run Ingestion & Start Servers
1. Compile the used car database from CSV:
   ```bash
   python db_importer.py
   ```
2. Start the FastAPI backend server (Port 8000):
   ```bash
   uvicorn api.index:app --port 8000 --reload
   ```
3. Start the React client (Port 5173) in a new terminal:
   ```bash
   npm run dev
   ```

Open **`http://localhost:5173`** in your browser.

---

## 🧪 Running Unit Tests
You can verify the database structures and API health checks by running:
```bash
python -m pytest api/test_backend.py
```
