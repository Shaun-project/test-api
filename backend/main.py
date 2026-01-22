from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import os
import time
from typing import Optional, List
from dotenv import load_dotenv
import json

load_dotenv()

app = FastAPI(title="London Journey Planner API", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
TFL_APP_ID = os.getenv("TFL_APP_ID")
TFL_APP_KEY = os.getenv("TFL_APP_KEY")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2:7b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Data models
class JourneyLeg(BaseModel):
    mode: str
    departure: str
    arrival: str
    duration: int

class Journey(BaseModel):
    duration: int
    startTime: str
    arrivalTime: str
    legs: List[JourneyLeg]

class ExplanationRequest(BaseModel):
    from_station: str
    to_station: str
    journey_index: int = 0

# ========== OLLAMA FUNCTIONS ==========

def check_ollama_available() -> bool:
    """Check if Ollama is running and accessible"""
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"✅ Ollama available. Models: {[m['name'] for m in models]}")
            
            # Check if our model is available
            for model in models:
                if OLLAMA_MODEL in model["name"]:
                    return True
            print(f"⚠️ Model '{OLLAMA_MODEL}' not found in Ollama")
            return False
        return False
    except Exception as e:
        print(f"❌ Ollama not available: {e}")
        return False

def generate_with_ollama(prompt: str) -> str:
    """Generate text using Ollama LLM"""
    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 300
                    }
                },
                timeout=45
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                print(f"⚠️ Ollama API error {response.status_code}: {response.text}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    
        except requests.exceptions.Timeout:
            print(f"⚠️ Ollama timeout (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2)
        except Exception as e:
            print(f"⚠️ Ollama error: {e}")
            break
    
    return ""  # Return empty string if all retries fail

# ========== TfL API FUNCTIONS ==========

def find_best_station_id(station_name: str) -> Optional[str]:
    """Search for a station and return the best matching ID."""
    search_url = f"https://api.tfl.gov.uk/StopPoint/Search/{station_name}"
    
    params = {
        "modes": "tube,dlr,overground,tram,national-rail,bus",
        "maxResults": 5
    }
    
    if TFL_APP_ID and TFL_APP_KEY:
        params["app_id"] = TFL_APP_ID
        params["app_key"] = TFL_APP_KEY

    try:
        response = requests.get(search_url, params=params, timeout=10)
        
        if response.status_code != 200:
            print(f"TfL Search API error: {response.status_code}")
            return None
        
        data = response.json()
        
        if not data.get("matches"):
            return None
        
        best_match = data["matches"][0]
        return best_match.get("icsId") or best_match.get("id")
        
    except requests.exceptions.RequestException as e:
        print(f"Error searching for station: {e}")
        return None

def format_journey_for_prompt(journey_data: dict, from_station: str, to_station: str) -> str:
    """Format journey data for LLM prompt"""
    legs_info = []
    for i, leg in enumerate(journey_data.get("legs", []), 1):
        leg_desc = f"{i}. Take {leg['mode']} from {leg['departure']} to {leg['arrival']}"
        if leg.get('duration'):
            leg_desc += f" ({leg['duration']} minutes)"
        legs_info.append(leg_desc)
    
    journey_text = f"""
JOURNEY PLAN:
- From: {from_station}
- To: {to_station}
- Total duration: {journey_data.get('duration', 0)} minutes
- Departure: {journey_data.get('startTime', 'N/A')}
- Arrival: {journey_data.get('arrivalTime', 'N/A')}
- Number of changes: {len(journey_data.get('legs', [])) - 1}

ROUTE DETAILS:
{chr(10).join(legs_info)}
"""
    return journey_text.strip()

def generate_journey_explanation(journey_data: dict, from_station: str, to_station: str) -> str:
    """
    Generate an explanation for a journey using Ollama LLM with fallback.
    """
    # Always create a basic explanation first
    legs = journey_data.get("legs", [])
    changes = len(legs) - 1
    modes = list(set(leg.get("mode", "Unknown") for leg in legs))
    
    # Create basic explanation
    basic_explanation = f"""## Journey Summary

**Route:** {from_station} → {to_station}
**Total time:** {journey_data.get('duration', 0)} minutes
**Changes required:** {changes}
**Transport modes:** {', '.join(modes)}

**Step-by-step route:**
"""
    
    for i, leg in enumerate(legs):
        basic_explanation += f"\n{i+1}. **{leg['mode']}** from {leg['departure']} to {leg['arrival']}"
        if leg.get('duration'):
            basic_explanation += f" ({leg['duration']} minutes)"
    
    basic_explanation += "\n\n**General tips:**"
    basic_explanation += "\n• Check TfL service status before traveling"
    basic_explanation += "\n• Allow extra time during peak hours (7-9 AM, 5-7 PM)"
    basic_explanation += "\n• Use contactless payment or Oyster card for best fares"
    
    # Try to get AI enhancement if Ollama is available
    if check_ollama_available():
        journey_text = format_journey_for_prompt(journey_data, from_station, to_station)
        
        prompt = f"""You are a London transport expert. Analyze this journey plan:

{journey_text}

Provide a concise analysis with:
1. Is this an efficient route? (consider time and changes)
2. Any potential issues or tricky interchanges?
3. One practical tip for this specific journey
4. Alternative options to consider

Keep response under 200 words. Be specific about London transport."""

        try:
            ai_response = generate_with_ollama(prompt)
            if ai_response:
                return f"{basic_explanation}\n\n---\n\n**🤖 AI Analysis:**\n\n{ai_response}"
        except Exception as e:
            print(f"AI generation failed: {e}")
    
    # Fallback: return basic explanation
    return f"{basic_explanation}\n\n*Note: AI analysis is currently unavailable.*"

# ========== API ENDPOINTS ==========

@app.get("/")
async def root():
    """Health check and service status"""
    ollama_status = "available" if check_ollama_available() else "unavailable"
    
    return {
        "status": "online",
        "service": "London Journey Planner API",
        "version": "1.0.0",
        "ollama": ollama_status,
        "ollama_model": OLLAMA_MODEL,
        "endpoints": [
            {"GET /": "Health check"},
            {"GET /journey": "Get journey plans (from_, to)"},
            {"GET /journey/explain": "Get AI explanation (from_, to, index)"},
            {"GET /status": "Detailed service status"}
        ]
    }

@app.get("/status")
async def status():
    """Detailed service status"""
    ollama_available = check_ollama_available()
    status_info = {
        "backend": "running",
        "tfl_api": "configured" if TFL_APP_ID and TFL_APP_KEY else "unconfigured",
        "ollama": {
            "available": ollama_available,
            "host": OLLAMA_HOST,
            "model": OLLAMA_MODEL,
            "status": "connected" if ollama_available else "disconnected"
        }
    }
    
    if ollama_available:
        try:
            response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
            models = response.json().get("models", [])
            status_info["ollama"]["models"] = [m["name"] for m in models]
        except:
            pass
    
    return status_info

@app.get("/journey")
async def get_journey(from_: str, to: str):
    """
    Fetch journey results from TfL Journey Planner API.
    """
    if not from_ or not to:
        raise HTTPException(status_code=400, detail="Both 'from_' and 'to' parameters are required")
    
    # Get station IDs
    from_id = find_best_station_id(from_)
    to_id = find_best_station_id(to)
    
    if not from_id or not to_id:
        raise HTTPException(status_code=404, detail="Could not find valid stations")
    
    # Fetch journey from TfL
    url = f"https://api.tfl.gov.uk/Journey/JourneyResults/{from_id}/to/{to_id}"
    params = {
        "mode": "tube,dlr,overground,tram,national-rail,bus",
        "timeIs": "departing",
        "nationalSearch": "true",
    }
    
    if TFL_APP_ID and TFL_APP_KEY:
        params["app_id"] = TFL_APP_ID
        params["app_key"] = TFL_APP_KEY

    try:
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail=f"TfL API error: {response.status_code}")
        
        data = response.json()
        journeys = []
        
        for journey in data.get("journeys", []):
            legs = []
            for leg in journey.get("legs", []):
                legs.append({
                    "mode": leg["mode"]["name"],
                    "departure": leg["departurePoint"]["commonName"],
                    "arrival": leg["arrivalPoint"]["commonName"],
                    "duration": leg.get("duration", 0)
                })
            
            journeys.append({
                "duration": journey["duration"],
                "startTime": journey["startDateTime"],
                "arrivalTime": journey["arrivalDateTime"],
                "legs": legs
            })
        
        if not journeys:
            raise HTTPException(status_code=404, detail="No journeys found")
        
        return {
            "from": from_,
            "to": to,
            "from_id": from_id,
            "to_id": to_id,
            "journeys": journeys,
            "count": len(journeys),
            "ollama_available": check_ollama_available()
        }
        
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="TfL API timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/journey/explain")
async def explain_journey(from_: str, to: str, index: int = 0):
    """
    Get AI explanation for a specific journey.
    """
    if not from_ or not to:
        raise HTTPException(status_code=400, detail="Both 'from_' and 'to' parameters are required")
    
    if index < 0:
        raise HTTPException(status_code=400, detail="Index must be 0 or greater")
    
    try:
        # Get journey data first
        journey_result = await get_journey(from_, to)
        journeys = journey_result.get("journeys", [])
        
        if index >= len(journeys):
            raise HTTPException(
                status_code=400,
                detail=f"Journey index {index} out of range. Only {len(journeys)} available."
            )
        
        # Get the specific journey
        journey = journeys[index]
        
        # Generate explanation
        explanation = generate_journey_explanation(journey, from_, to)
        
        return {
            "explanation": explanation,
            "journey_index": index,
            "from": from_,
            "to": to,
            "journey_summary": {
                "duration": journey["duration"],
                "changes": len(journey["legs"]) - 1,
                "modes": list(set(leg["mode"] for leg in journey["legs"]))
            },
            "ollama_used": check_ollama_available()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate explanation: {str(e)}")

@app.post("/explain/custom")
async def explain_custom_journey(request: ExplanationRequest):
    """
    Explain a journey with custom data (for frontend that already has journey data).
    """
    try:
        # This endpoint would typically receive pre-fetched journey data
        # For now, we'll fetch it fresh
        journey_result = await get_journey(request.from_station, request.to_station)
        journeys = journey_result.get("journeys", [])
        
        if request.journey_index >= len(journeys):
            raise HTTPException(status_code=400, detail="Invalid journey index")
        
        journey = journeys[request.journey_index]
        explanation = generate_journey_explanation(journey, request.from_station, request.to_station)
        
        return {
            "explanation": explanation,
            "ollama_available": check_ollama_available()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚇 London Journey Planner API")
    print("=" * 60)
    
    # Check services
    print("\n🔍 Checking services...")
    
    # Check Ollama
    ollama_ok = check_ollama_available()
    if ollama_ok:
        print("✅ Ollama: Connected")
    else:
        print("⚠️ Ollama: Not connected (AI explanations will use fallback)")
    
    # Check TfL credentials
    if TFL_APP_ID and TFL_APP_KEY:
        print("✅ TfL API: Credentials configured")
    else:
        print("⚠️ TfL API: Using public access (rate limited)")
    
    print(f"\n🌐 Starting server on http://localhost:8000")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("\n✨ Ready to serve journey plans!")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)