from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.auth import require_authenticated_user
from app.database import get_db
from app.models.point_transaction import PointTransaction
from app.models.profile import Profile
from app.schemas.points import PointsResponse
router = APIRouter(prefix="/points", tags=["points"])
@router.get("/me", response_model=PointsResponse, summary="Get current user's points")
def get_my_points(current_profile: Profile = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    transactions = db.query(PointTransaction).filter(PointTransaction.user_id == current_profile.id).order_by(PointTransaction.created_at.desc()).all()
    return PointsResponse(points=current_profile.points or 0, transactions=transactions)
