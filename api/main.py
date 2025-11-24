import os
import sys

import dotenv
from fastapi import Depends, FastAPI
from sqlalchemy import desc
from sqlalchemy.orm import Session

from shared.database import create_tables, get_db
from shared.models import WeatherData

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import get_db, create_tables
from shared.models import WeatherData

dotenv.load_dotenv()

app = FastAPI(title="Weather Station API")


@app.on_event("startup")
def startup():
    create_tables()


@app.get("/")
def read_root():
    return {"message": "Weather Station API"}


@app.get("/api/current")
def get_current_weather(db: Session = Depends(get_db)):
    """Получить последние данные"""
    latest = db.query(WeatherData).order_by(desc(WeatherData.timestamp)).first()
    if not latest:
        return {"error": "No data available"}

    return {
        "temperature": latest.temperature,
        "humidity": latest.humidity,
        "timestamp": latest.timestamp.isoformat(),
    }


@app.get("/api/history")
def get_history(db: Session = Depends(get_db), limit: int = 10):
    """Получить исторические данные"""
    records = (
        db.query(WeatherData).order_by(desc(WeatherData.timestamp)).limit(limit).all()
    )

    return [
        {
            "temperature": r.temperature,
            "humidity": r.humidity,
            "timestamp": r.timestamp.isoformat(),
        }
        for r in records
    ]


def main():
    import uvicorn

    host = os.getenv("API_HOST")
    port = os.getenv("API_PORT")
    if host == None or port == None:
        print("API_HOST или API_PORT переменные среды отсутствует")
        return
    port = int(port)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
