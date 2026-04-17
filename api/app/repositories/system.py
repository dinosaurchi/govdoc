from app.repositories.base import CRUDBase
from app.models.system import Role, Department, AuditEvent, DemoScenario, PromptVersion
from pydantic import BaseModel

class CRUDRole(CRUDBase[Role, BaseModel, BaseModel]):
    pass

class CRUDDepartment(CRUDBase[Department, BaseModel, BaseModel]):
    pass

class CRUDAuditEvent(CRUDBase[AuditEvent, BaseModel, BaseModel]):
    pass

class CRUDDemoScenario(CRUDBase[DemoScenario, BaseModel, BaseModel]):
    pass

class CRUDPromptVersion(CRUDBase[PromptVersion, BaseModel, BaseModel]):
    pass

role = CRUDRole(Role)
department = CRUDDepartment(Department)
audit_event = CRUDAuditEvent(AuditEvent)
demo_scenario = CRUDDemoScenario(DemoScenario)
prompt_version = CRUDPromptVersion(PromptVersion)
