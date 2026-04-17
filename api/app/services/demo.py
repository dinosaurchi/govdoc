from sqlalchemy.orm import Session
from app.repositories import document as doc_repo
from app.repositories import system as sys_repo
from app.models.document import WorkflowState, DocumentType
from typing import List

class DemoService:
    def __init__(self, db: Session):
        self.db = db

    async def seed_baseline(self):
        # 1. Seed Roles
        roles = ["Intake Clerk", "Department Reviewer", "Consultant", "Supervisor"]
        for r_name in roles:
            existing = sys_repo.role.get_multi(self.db, limit=100)
            if not any(r.name == r_name for r in existing):
                sys_repo.role.create(self.db, obj_in={"name": r_name, "description": f"Standard {r_name} role"})

        # 2. Seed Departments
        depts = [
            {"name": "Văn phòng Bộ", "code": "VP"},
            {"name": "Vụ Kế hoạch - Tài chính", "code": "KHTC"},
            {"name": "Vụ Khoa học và Công nghệ", "code": "KHCN"},
            {"name": "Vụ Pháp chế", "code": "PC"},
            {"name": "Cục Công nghiệp", "code": "CN"}
        ]
        for d_info in depts:
            existing = sys_repo.department.get_multi(self.db, limit=100)
            if not any(d.code == d_info["code"] for d in existing):
                sys_repo.department.create(self.db, obj_in=d_info)

    async def seed_scenarios(self):
        # Ensure baseline first
        await self.seed_baseline()
        
        # Scenario 1: Hero Flow (Clean path)
        doc1 = doc_repo.document.create(self.db, obj_in={
            "title": "V/v Phê duyệt kế hoạch bảo trì hệ thống IT 2026",
            "doc_type": DocumentType.cong_van,
            "state": WorkflowState.assigned_to_department
        })
        
        # Scenario 2: Ambiguity Flow (Needs clarification)
        doc2 = doc_repo.document.create(self.db, obj_in={
            "title": "Đề xuất điều chỉnh hạn mức ngân sách dự phòng",
            "doc_type": DocumentType.to_trinh,
            "state": WorkflowState.intake_received
        })

        # Scenario 3: Consultation Flow (Needs expert opinion)
        doc3 = doc_repo.document.create(self.db, obj_in={
            "title": "Hợp đồng hợp tác quốc tế về chuyển giao công nghệ",
            "doc_type": DocumentType.quyet_dinh,
            "state": WorkflowState.consultation_requested
        })
        
        return [doc1, doc2, doc3]
