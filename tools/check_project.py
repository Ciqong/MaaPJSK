import json
import py_compile
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name == "tools" else SCRIPT_DIR


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    raise SystemExit(1)


def walk_nodes(resource_dir: Path):
    pipeline_dir = resource_dir / "pipeline"
    if not pipeline_dir.exists():
        fail(f"Missing pipeline directory: {pipeline_dir}")

    nodes = {}
    for path in pipeline_dir.rglob("*.json"):
        data = load_json(path)
        if not isinstance(data, dict):
            fail(f"Pipeline file must be an object: {path}")
        for name, node in data.items():
            if name in nodes:
                fail(f"Duplicate node name: {name}")
            nodes[name] = (path, node)
    return nodes


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def strip_node_attr(name):
    if isinstance(name, dict):
        name = name.get("name", "")
    if not isinstance(name, str):
        return ""
    if name.startswith("[JumpBack]"):
        return name[len("[JumpBack]") :]
    if name.startswith("[Anchor]"):
        return ""
    return name


def main() -> int:
    interface_path = ROOT / "assets" / "interface.json"
    resource_dir = ROOT / "assets" / "resource"
    if not interface_path.exists():
        interface_path = ROOT / "interface.json"
        resource_dir = ROOT / "resource"

    interface = load_json(interface_path)
    nodes = walk_nodes(resource_dir)
    image_dir = resource_dir / "image"

    for task in interface.get("task", []):
        entry = task.get("entry")
        if entry not in nodes:
            fail(f"Task entry not found: {entry}")

    for node_name, (path, node) in nodes.items():
        for field in ("next", "on_error"):
            for raw_target in as_list(node.get(field)):
                target = strip_node_attr(raw_target)
                if target and target not in nodes:
                    fail(f"{node_name}.{field} references missing node {target} in {path}")

        for template in as_list(node.get("template")):
            if template and not (image_dir / template).exists():
                fail(f"{node_name} references missing template {template}")

    for agent_file in (ROOT / "agent").glob("*.py"):
        py_compile.compile(str(agent_file), doraise=True)

    print(f"OK: {len(nodes)} pipeline nodes checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
