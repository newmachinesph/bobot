from datetime import datetime

from pydantic import BaseModel


class PulseResponse(BaseModel):
    national_price_index: dict = {}
    civic_sentiment: dict = {}
    misinformation_heatmap: dict = {}
    top_bots: list = []
    active_debates: list = []
    timestamp: datetime | None = None

    model_config = {"from_attributes": True}


class PriceIndexResponse(BaseModel):
    items: list[dict] = []
    region: str | None = None
    period: str = "7d"


class SentimentResponse(BaseModel):
    topics: list[dict] = []
    baryo: str | None = None
    period: str = "7d"


class MisinfoResponse(BaseModel):
    regions: list[dict] = []
    period: str = "7d"
