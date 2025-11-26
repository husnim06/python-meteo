import os
import sys

import dotenv
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import create_tables, get_db
from shared.models import WeatherData


dotenv.load_dotenv()


app = FastAPI(
    title="Weather Station API",
    description="API для получения данных о температуре и влажности",
    version="1.1.0",
)


class WeatherResponse(BaseModel):
    temperature: float
    humidity: float
    timestamp: str


@app.get("/")
async def read_root():
    return {"message": "Weather Station API"}


@app.get(
    "/api/current",
    response_model=WeatherResponse,
    summary="Текущие показания",
    responses={
        404: {"description": "Данные не найдены"},
        500: {"description": "Ошибка сервера"},
    },
)
async def get_current_weather(db: Session = Depends(get_db)):
    """Получить последние данные"""
    try:
        latest = db.query(WeatherData).order_by(desc(WeatherData.timestamp)).first()
        if not latest:
            raise HTTPException(status_code=404, detail="No weather data available")

        return {
            "temperature": latest.temperature,
            "humidity": latest.humidity,
            "timestamp": latest.timestamp.isoformat(),
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Database error")


@app.get("/health")
async def healthcheck():
    return {"status": "healthy"}


def main():
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))

    create_tables()

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
