from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# Import Google GenAI (New SDK)
from google import genai
from google.genai import types

# Load local environment variables from .env if present
load_dotenv()

app = FastAPI()

# Check which API key is configured
openai_key = os.getenv("OPENAI_API_KEY")
gemini_key = os.getenv("GEMINI_API_KEY")

# Initialize clients
openai_client = OpenAI(api_key=openai_key) if openai_key else None

if gemini_key:
    # Initialize the new Google GenAI client
    gemini_client = genai.Client(api_key=gemini_key)
else:
    gemini_client = None

# Check database path
DB_PATH = 'cardekho_cars.db'
if not os.path.exists(DB_PATH):
    DB_PATH = '../cardekho_cars.db'

class ChatRequest(BaseModel):
    message: str
    history: list = []

# Schema definition for system prompt guidance
DB_SCHEMA = """
Table Name: cars
Columns:
- car_name: string (e.g. 'Maruti Alto', 'Hyundai Grand')
- brand: string (e.g. 'Maruti', 'Hyundai', 'Ford')
- model: string (e.g. 'Alto', 'Grand', 'i20')
- vehicle_age: integer (age in years, e.g. 9, 5)
- km_driven: integer (e.g. 120000, 20000)
- seller_type: string ('Individual' or 'Dealer')
- fuel_type: string ('Petrol', 'Diesel', 'CNG', 'LPG', 'Electric')
- transmission_type: string ('Manual', 'Automatic')
- mileage: float (km per liter, e.g. 19.7, 18.9)
- engine: integer (CC engine size, e.g. 796, 1197)
- max_power: float (BHP power, e.g. 46.3, 82.0)
- seats: integer (e.g. 5, 7)
- selling_price: integer (price in Indian Rupees, e.g. 120000, 550000)
"""

SQL_SYSTEM_PROMPT = f"""
You are an expert database assistant converting user queries about used cars into SQLite queries.
Use this database schema:
{DB_SCHEMA}

RULES:
1. Return ONLY a JSON object containing the key "sql_query". Do not write markdown blocks other than valid JSON.
2. The query must be a valid SQLite query.
3. Case-insensitive searches for strings must use LIKE. (e.g., brand LIKE '%maruti%')
4. Always include a LIMIT clause (max 15 rows) to avoid overwhelming the system.
5. If the user asks for general recommendations, search by popular filters (e.g., low price, low age, high mileage).
"""

RECOMMENDER_SYSTEM_PROMPT = """
You are a friendly, expert Used Car Advisor at CarDekho.
Given the user's request and the list of matching cars returned from the database, explain:
1. Why these cars fit their requirements.
2. The key highlights of these models (e.g. fuel type, transmission, cost-benefit).
3. Offer tips on negotiating or what details to inspect (mileage, age).

Keep your response conversational, concise, and formatted in clean Markdown.
If no cars are returned, explain kindly and suggest adjusting their parameters (e.g. budget, brand).
"""

@app.get("/api/health")
def health():
    db_exists = os.path.exists(DB_PATH)
    active_provider = None
    if gemini_key:
        active_provider = "Gemini"
    elif openai_key:
        active_provider = "OpenAI"
        
    return {
        "status": "healthy",
        "openai_configured": openai_client is not None,
        "gemini_configured": gemini_client is not None,
        "active_provider": active_provider,
        "database_exists": db_exists,
        "database_path": os.path.abspath(DB_PATH) if db_exists else None
    }

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not os.path.exists(DB_PATH):
        raise HTTPException(
            status_code=500, 
            detail=f"Database file '{DB_PATH}' not found. Please run the ingestion script 'db_importer.py' first."
        )
        
    if not gemini_client and not openai_client:
        raise HTTPException(
            status_code=400,
            detail="No AI Provider configured. Please add GEMINI_API_KEY or OPENAI_API_KEY to your .env file."
        )
        
    try:
        query = None
        cars = []
        explanation = ""
        
        # Determine active provider
        if gemini_client:
            # === GOOGLE GEMINI (NEW SDK) EXECUTION ===
            # Step 1: SQL Generation in JSON mode using gemini-2.5-flash
            sql_prompt = f"{SQL_SYSTEM_PROMPT}\nUser query: {request.message}"
            sql_response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=sql_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            sql_json = json.loads(sql_response.text)
            query = sql_json.get("sql_query")
            
            # Step 2: Query SQLite database
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            try:
                cursor.execute(query)
                rows = cursor.fetchall()
                cars = [dict(r) for r in rows]
            except Exception as sql_err:
                conn.close()
                return {
                    "message": f"I had trouble executing the database query. Try rephrasing your search request! (Failed query details: {sql_err})",
                    "cars": [],
                    "sql": query
                }
            conn.close()
            
            # Step 3: Explanation & Summary
            recommender_prompt = f"{RECOMMENDER_SYSTEM_PROMPT}\nUser prompt: {request.message}\nDatabase results: {json.dumps(cars)}"
            recommender_response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=recommender_prompt
            )
            explanation = recommender_response.text
            
        else:
            # === OPENAI EXECUTION ===
            # Step 1: SQL Generation
            sql_generation_messages = [
                {"role": "system", "content": SQL_SYSTEM_PROMPT},
                {"role": "user", "content": f"User query: {request.message}"}
            ]
            sql_response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=sql_generation_messages,
                response_format={"type": "json_object"}
            )
            sql_json = json.loads(sql_response.choices[0].message.content)
            query = sql_json.get("sql_query")
            
            # Step 2: Query SQLite database
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            try:
                cursor.execute(query)
                rows = cursor.fetchall()
                cars = [dict(r) for r in rows]
            except Exception as sql_err:
                conn.close()
                return {
                    "message": f"I had trouble executing the database query. Try rephrasing your search request! (Failed query details: {sql_err})",
                    "cars": [],
                    "sql": query
                }
            conn.close()
            
            # Step 3: Explanation & Summary
            recommender_messages = [
                {"role": "system", "content": RECOMMENDER_SYSTEM_PROMPT},
                {"role": "user", "content": f"User prompt: {request.message}\nDatabase results: {json.dumps(cars)}"}
            ]
            recommender_response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=recommender_messages
            )
            explanation = recommender_response.choices[0].message.content
            
        return {
            "message": explanation,
            "cars": cars,
            "sql": query
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
