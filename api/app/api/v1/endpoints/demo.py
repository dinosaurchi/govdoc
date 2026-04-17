from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api import deps
from app.services.demo import DemoService

router = APIRouter()

@router.post("/seed")
async def seed_data(db: Session = Depends(deps.get_db)):
    demo = DemoService(db)
    docs = await demo.seed_scenarios()
    return {"status": "success", "seeded_documents_count": len(docs)}

@router.get("/scenarios")
async def list_scenarios():
    return [
        {"id": 1, "name": "Hero Flow", "description": "Clean path from intake to closeout"},
        {"id": 2, "name": "Ambiguity Flow", "description": "Needs data extraction clarification"},
        {"id": 3, "name": "Consultation Flow", "description": "Multi-departmental review path"}
    ]
