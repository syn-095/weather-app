from dataclasses import dataclass, field, asdict
from typing import Optional, List

@dataclass
class HourlyPoint:
    time: str
    temperature_c: float
    feels_like_c: Optional[float]
    humidity_pct: float
    precipitation_mm: float
    wind_speed_kmh: float
    wind_direction_deg: Optional[int]
    weather_code: int
    description: str
    icon: str
    source: str

    def to_dict(self):
        return asdict(self)

@dataclass
class DailyPoint:
    date: str
    temp_max_c: float
    temp_min_c: float
    temp_avg_c: float
    precipitation_mm: float
    humidity_avg_pct: float
    wind_max_kmh: float
    wind_avg_kmh: float
    weather_code: int
    description: str
    icon: str
    sunrise: Optional[str]
    sunset: Optional[str]
    source: str
    hourly: List[HourlyPoint] = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        d["hourly"] = [h.to_dict() for h in self.hourly]
        return d

@dataclass
class WeatherResponse:
    location: str
    latitude: float
    longitude: float
    timezone: str
    current: Optional[HourlyPoint]
    daily: List[DailyPoint]
    aggregated_daily: List[dict]
    sources: List[str]
    fetched_at: str

    def to_dict(self):
        return {
            "location": self.location,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timezone": self.timezone,
            "current": self.current.to_dict() if self.current else None,
            "daily": [d.to_dict() for d in self.daily],
            "aggregated_daily": self.aggregated_daily,
            "sources": self.sources,
            "fetched_at": self.fetched_at,
        }