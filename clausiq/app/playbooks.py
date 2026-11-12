"""Playbook loader."""
import yaml

from .config import PLAYBOOKS_DIR


def get_playbook(playbook_id: str) -> dict | None:
    path = PLAYBOOKS_DIR / f"{playbook_id}.yaml"
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    data["id"] = data.get("id", playbook_id)
    data["rule_count"] = len(data.get("rules", []))
    return data


def list_playbooks() -> list[dict]:
    playbooks = []
    for path in sorted(PLAYBOOKS_DIR.glob("*.yaml")):
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        playbooks.append(
            {
                "id": data.get("id", path.stem),
                "name": data.get("name", path.stem),
                "organization": data.get("organization", ""),
                "description": data.get("description", ""),
                "rule_count": len(data.get("rules", [])),
                "rules": data.get("rules", []),
            }
        )
    return playbooks
