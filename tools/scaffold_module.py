"""Generate a canonical module skeleton for PQTS."""

from __future__ import annotations

import argparse
from pathlib import Path

TEMPLATE = '''"""{title} module descriptor."""

from __future__ import annotations

from contracts import ModuleDescriptor
from modules.base import StaticModule


class {class_name}(StaticModule):
    def __init__(self) -> None:
        super().__init__(
            descriptor=ModuleDescriptor(
                name="{name}",
                requires={requires},
                provides={provides},
                description="{description}",
            )
        )
'''


def _snake_to_title(value: str) -> str:
    return value.replace("_", " ").title()


def _snake_to_class(value: str) -> str:
    return "".join(part.capitalize() for part in value.split("_")) + "Module"


def _tuple_literal(values: list[str]) -> str:
    if not values:
        return "()"
    if len(values) == 1:
        return f"({values[0]!r},)"
    return "(" + ", ".join(repr(item) for item in values) + ")"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="Module name in snake_case (e.g. order_intelligence)")
    parser.add_argument(
        "--requires",
        default="",
        help="Comma-separated module dependencies.",
    )
    parser.add_argument(
        "--provides",
        default="",
        help="Comma-separated capability names.",
    )
    parser.add_argument(
        "--description",
        default="",
        help="Module description.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root path.",
    )
    args = parser.parse_args()

    name = args.name.strip()
    if not name or any(ch for ch in name if not (ch.islower() or ch.isdigit() or ch == "_")):
        raise ValueError("module name must be snake_case (lowercase letters, digits, underscores)")

    requires = [item.strip() for item in args.requires.split(",") if item.strip()]
    provides = [item.strip() for item in args.provides.split(",") if item.strip()]

    repo_root = Path(args.root).resolve()
    module_path = repo_root / "modules" / f"{name}.py"
    if module_path.exists():
        raise FileExistsError(f"module file already exists: {module_path}")

    description = args.description.strip() or f"Owns {name.replace('_', ' ')} responsibilities."
    content = TEMPLATE.format(
        title=_snake_to_title(name),
        class_name=_snake_to_class(name),
        name=name,
        requires=_tuple_literal(requires),
        provides=_tuple_literal(provides),
        description=description,
    )

    module_path.parent.mkdir(parents=True, exist_ok=True)
    module_path.write_text(content, encoding="utf-8")

    print(f"Created module skeleton: {module_path}")
    print("Next: import and register this module in modules/__init__.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
