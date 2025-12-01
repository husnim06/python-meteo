from datetime import datetime
from typing import Dict

from sqlalchemy import CheckConstraint, Column, DateTime, Float, Integer

from .database import Base


class WeatherData(Base):
    __tablename__ = "weather_data"

    id = Column(Integer, primary_key=True, index=True)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "temperature BETWEEN -50 AND 60", name="reasonable_temperature"
        ),
        CheckConstraint("humidity BETWEEN 0 AND 100", name="reasonable_humidity"),
    )

    def to_dict(self) -> Dict:
        """Конвертирует запись в словарь для API"""
        return {
            "id": self.id,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "timestamp": self.timestamp.isoformat(),
        }
