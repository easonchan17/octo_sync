from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class FeatureRequest(BaseModel):
    processor_name: str = Field(..., description="Feature processor name")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parameters for feature processing")

class FeatureResponse(BaseModel):
    success: bool = Field(..., description="Whether the feature engineering succeeded")
    processor_name: str = Field(..., description="Feature processor name")
    output_files: list[str] = Field(default_factory=list, description="Generated output file paths")
    message: Optional[str] = Field(None, description="Response message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional response data")
