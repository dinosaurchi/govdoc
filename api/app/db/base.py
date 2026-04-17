# Import all the models, so that Base has them before being
# imported by Alembic
from app.db.base_class import Base  # noqa
from app.models.document import Document, DocumentFile, ExtractedArtifact, AIAnalysis, RoutingDecision, ConsultationNote  # noqa
from app.models.system import Role, Department, AuditEvent, DemoScenario, PromptVersion  # noqa
