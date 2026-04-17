"""Role utility helpers."""

from app.api.deps import _load_roles, CurrentRole


def get_all_roles() -> list[dict]:
    """Get all available roles from the loaded config."""
    roles = _load_roles()
    return [{"id": r.id, "label": r.label, "allowed_actions": r.allowed_actions} for r in roles.values()]


def get_role_id_by_label(label: str) -> str | None:
    """Look up a Role by its label and return its string PK id."""
    roles = _load_roles()
    for r in roles.values():
        if r.label == label:
            return r.id
    return None
