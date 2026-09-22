from datetime import datetime
import uuid
from pydantic import BaseModel, ConfigDict
class PointTransactionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    points: int
    reason: str
    issue_id: uuid.UUID | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
class PointsResponse(BaseModel):
    points: int
    transactions: list[PointTransactionResponse]
