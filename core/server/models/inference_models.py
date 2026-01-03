from pydantic import BaseModel
from typing import Dict


class PredictionResponse(BaseModel):
    model_version: str
    probabilities: Dict[str, float]
    prediction: int
