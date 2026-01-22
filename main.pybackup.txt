from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all for local testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TFL_APP_ID = os.getenv("TFL_APP_ID")
TFL_APP_KEY = os.getenv("TFL_APP_KEY")


def find_best_station_id(station_name: str):
    """
    Search for a station and return the best matching ID.
    """
    search_url = f"https://api.tfl.gov.uk/StopPoint/Search/{station_name}"
    
    params = {
        "modes": "tube,dlr,overground,tram,national-rail,bus",
        "maxResults": 5
    }
    
    if TFL_APP_ID and TFL_APP_KEY:
        params["app_id"] = TFL_APP_ID
        params["app_key"] = TFL_APP_KEY

    response = requests.get(search_url, params=params)
    
    if response.status_code != 200:
        return None
    
    data = response.json()
    
    if not data.get("matches"):
        return None
    
    # Return the first (most relevant) match's ID
    best_match = data["matches"][0]
    return best_match.get("icsId") or best_match.get("id")


@app.get("/journey")
def get_journey(from_: str, to: str):
    """
    Fetch journey results from TfL Journey Planner API using station IDs.
    """
    # First, get the station IDs for better accuracy
    from_id = find_best_station_id(from_)
    to_id = find_best_station_id(to)
    
    if not from_id or not to_id:
        return {"error": "Could not find valid stations for the provided names"}
    
    base_url = "https://api.tfl.gov.uk/Journey/JourneyResults"
    
    # Use station IDs instead of names for more precise results
    url = f"{base_url}/{from_id}/to/{to_id}"

    params = {
        "mode": "tube,dlr,overground,tram,national-rail,bus",
        "timeIs": "departing",
        "nationalSearch": "true",
    }

    if TFL_APP_ID and TFL_APP_KEY:
        params["app_id"] = TFL_APP_ID
        params["app_key"] = TFL_APP_KEY

    response = requests.get(url, params=params)
    print("TfL API Status code:", response.status_code)
    print("TfL API Request URL:", response.url)
    
    if response.status_code != 200:
        error_detail = f"TfL API returned {response.status_code}"
        try:
            error_data = response.json()
            error_detail = error_data.get("message", error_detail)
        except:
            pass
        return {"error": f"Failed to fetch journey data: {error_detail}"}

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
    
    return {
        "from": from_,
        "to": to,
        "from_id": from_id,
        "to_id": to_id,
        "journeys": journeys
    }