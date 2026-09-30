from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models.cruise import Cruise
from app.db.session import get_db
from app.schemas.cruise import CruiseCreate, CruiseRead

router = APIRouter()


@router.get("", response_model=list[CruiseRead])
def list_cruises(db: Session = Depends(get_db)) -> list[Cruise]:
    return db.query(Cruise).order_by(Cruise.year.desc(), Cruise.name).all()


@router.post("", response_model=CruiseRead, status_code=201)
def create_cruise(body: CruiseCreate, db: Session = Depends(get_db)) -> Cruise:
    cruise = Cruise(
        name=body.name,
        year=body.year,
        start_date=body.start_date,
        end_date=body.end_date,
    )
    db.add(cruise)
    db.commit()
    db.refresh(cruise)
    return cruise
