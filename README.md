# London Commute Dashboard

A web application for planning journeys across London's transport network using the TfL (Transport for London) API.

## Features

- 🔍 **Real-time station search** with autocomplete suggestions
- 🚆 **Multi-mode journey planning** (Tube, DLR, Overground, Tram, National Rail, Bus)
- ⏱️ **Live journey times** and route information
- 📱 **Responsive design** that works on desktop and mobile

## Tech Stack

**Frontend:** React, CSS3
**Backend:** FastAPI (Python)
**API:** TfL Unified API

## Project Structure

london_commute_dashboard/
├── backend/
│ ├── main.py # FastAPI server
│ └── requirements.txt # Python dependencies
└── frontend/
├── src/
│ ├── App.js # Main React component
│ └── App.css # Styles
├── public/ # Static assets
└── package.json # Node dependencies



## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 14+

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend runs on `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

Frontend runs on `http://localhost:3000`



## API Endpoints

* `GET /journey?from_=StationName&to=StationName` - Get journey plans between two stations

## Environment Variables (Optional)

Create a `.env` file in the backend directory for higher API limits:

```bash
TFL_APP_ID=your_app_id
TFL_APP_KEY=your_app_key
```



## Usage

1. Enter your starting station in the "From" field
2. Enter your destination station in the "To" field
3. Select from the dropdown suggestions
4. Click "Get Journey" to see available routes
5. View journey duration, departure/arrival times, and route legs

## Example Search

* From: **Paddington**
* To: **Oxford Circus**

## License

MIT License
