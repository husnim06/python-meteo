import base64
import io
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import dotenv
import matplotlib
import matplotlib.pyplot as plt
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import create_tables, get_db
from shared.models import WeatherData

matplotlib.use("Agg")

dotenv.load_dotenv()

app = FastAPI(
    title="Weather Station API",
    description="API для получения данных о температуре и влажности",
    version="1.1.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"])

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class WeatherResponse(BaseModel):
    temperature: float
    humidity: float
    timestamp: str


class WeatherHistoryResponse(BaseModel):
    period: str
    data: List[WeatherResponse]
    stats: Dict[str, float]


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


@app.get("/api/history", response_model=WeatherHistoryResponse)
async def get_weather_history(
    db: Session = Depends(get_db),
    hours: int = 24,  # По умолчанию последние 24 часа
):
    """Получить историю данных с статистикой"""
    try:
        since = datetime.now(timezone.utc).replace(tzinfo=timezone.utc) - timedelta(
            hours=hours
        )

        records = (
            db.query(WeatherData)
            .filter(WeatherData.timestamp >= since)
            .order_by(WeatherData.timestamp)
            .all()
        )

        if not records:
            raise HTTPException(status_code=404, detail="No data for this period")

        # Расчет статистики
        temps: list = [r.temperature for r in records]
        humids: list = [r.humidity for r in records]

        stats = {
            "avg_temperature": sum(temps) / len(temps),
            "max_temperature": max(temps),
            "min_temperature": min(temps),
            "avg_humidity": sum(humids) / len(humids),
            "max_humidity": max(humids),
            "min_humidity": min(humids),
            "records_count": len(records),
        }

        return {
            "period": f"last_{hours}_hours",
            "data": [
                {
                    "temperature": r.temperature,
                    "humidity": r.humidity,
                    "timestamp": r.timestamp.isoformat(),
                }
                for r in records
            ],
            "stats": stats,
        }
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail="Database error")


@app.get("/api/chart")
async def generate_temperature_chart(
    db: Session = Depends(get_db),
    hours: int = 24,
    chart_type: str = "both",  # 'temperature', 'humidity', 'both'
):
    """Генерация графика в base64"""
    try:
        since = datetime.now(timezone.utc).replace(tzinfo=timezone.utc).replace(
            tzinfo=timezone.utc
        ) - timedelta(hours=hours)

        records = (
            db.query(WeatherData)
            .filter(WeatherData.timestamp >= since)
            .order_by(WeatherData.timestamp)
            .all()
        )

        if not records:
            raise HTTPException(status_code=404, detail="No data for chart")

        if len(records) < 2:
            raise HTTPException(
                status_code=400, detail="Not enough data points for chart"
            )

        # Подготовка данных
        timestamps: list = [r.timestamp for r in records]
        temperatures: list = [r.temperature for r in records]
        humidities: list = [r.humidity for r in records]

        # Создние графика с настройками для серверной среды
        plt.figure(figsize=(10, 6))

        # Настройка стиля для лучшего отображения
        plt.style.use("default")

        lines = []
        labels = []

        if chart_type in ["temperature", "both"]:
            line_temp = plt.plot(
                timestamps, temperatures, "r-", label="Температура (°C)", linewidth=2
            )
            plt.fill_between(timestamps, temperatures, alpha=0.2, color="red")
            lines.extend(line_temp)  # Добавление к существующему списку
            labels.append("Температура (°C)")

        if chart_type in ["humidity", "both"]:
            # Вторая ось Y для влажности
            if chart_type == "both":
                ax2 = plt.gca().twinx()
                line_humid = ax2.plot(
                    timestamps, humidities, "b-", label="Влажность (%)", linewidth=2
                )
                ax2.set_ylabel("Влажность (%)", color="blue")
                ax2.tick_params(axis="y", labelcolor="blue")
                ax2.set_ylim(0, 100)

                lines.extend(line_humid)  # Добавление к существующему списку
                labels.append("Влажность (%)")

                # Объединение легенд
                plt.legend(lines, labels, loc="upper left")
            else:
                line_humid = plt.plot(
                    timestamps, humidities, "b-", label="Влажность (%)", linewidth=2
                )
                plt.fill_between(timestamps, humidities, alpha=0.2, color="blue")
                lines.extend(line_humid)  # Добавление к существующему списку
                labels.append("Влажность (%)")
                plt.legend(lines, labels, loc="upper left")

        # ЕСЛИ ТОЛЬКО ОДНА ЛИНИЯ И ЕЩЕ НЕ ДОБАВИЛИ ЛЕГЕНДУ
        if chart_type != "both" and not (
            chart_type == "humidity" and chart_type != "both"
        ):
            # Для случая, когда chart_type = 'temperature'
            if lines:  # Проверка, что lines не пустой
                plt.legend(lines, labels, loc="upper left")

        if chart_type != "both":
            plt.ylabel("Значение")

        plt.title(f"Метеоданные за последние {hours} часов")
        plt.xlabel("Время")
        plt.grid(True, alpha=0.3)

        # Форматирование оси X для читаемости
        plt.gcf().autofmt_xdate()

        # Убеждаемся, что все помещается
        plt.tight_layout()

        # Конвертация в base64
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close()  # Важно: закрывается figure для освобождения памяти
        buf.seek(0)

        image_base64 = base64.b64encode(buf.read()).decode("utf-8")
        return {"image": f"data:image/png;base64,{image_base64}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        raise HTTPException(status_code=500, detail="Chart generation error")
    finally:
        plt.close("all")


@app.get("/health")
async def healthcheck():
    return {"status": "healthy"}


def main():
    import uvicorn

    host = os.getenv("API_HOST")
    port = os.getenv("API_PORT")

    if not host or not port:
        logger.error("API_HOST/API_PORT environment variable is required")
        return
    port = int(port)

    create_tables()

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
