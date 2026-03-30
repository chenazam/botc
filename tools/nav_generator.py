from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MKDOCS_FILE = PROJECT_ROOT / "mkdocs.yml"
DOCS_DIR = PROJECT_ROOT / "docs"
ROLES_DIR = DOCS_DIR / "roles"
SCRIPTS_DIR = DOCS_DIR / "scripts"
TYPES_DIR = ROLES_DIR / "types"

NAV_START_MARKER = "  # AUTO-GENERATED NAV START"
NAV_END_MARKER = "  # AUTO-GENERATED NAV END"

TYPE_PAGE_START_MARKER = "<!-- AUTO-GENERATED ROLE LIST START -->"
TYPE_PAGE_END_MARKER = "<!-- AUTO-GENERATED ROLE LIST END -->"

STRATEGY_INDEX_FILE = DOCS_DIR / "strategy" / "index.md"

STRATEGY_PAGE_START_MARKER = "<!-- AUTO-GENERATED STRATEGY LIST START -->"
STRATEGY_PAGE_END_MARKER = "<!-- AUTO-GENERATED STRATEGY LIST END -->"

SCRIPT_STRATEGY_PAGE_START_MARKER = "<!-- AUTO-GENERATED SCRIPT STRATEGY LIST START -->"
SCRIPT_STRATEGY_PAGE_END_MARKER = "<!-- AUTO-GENERATED SCRIPT STRATEGY LIST END -->"

PREFERRED_SCRIPT_ORDER = [
    "trouble_brewing",
    "sects_and_violets",
    "bad_moon_rising",
    "experimental",
]

EXCLUDED_ROLE_DIRS = {
    "types",
}

ROLE_TYPE_ORDER = [
    "townsfolk",
    "outsiders",
    "minions",
    "demons",
]

ROLE_TYPE_LABELS = {
    "townsfolk": "Townsfolk",
    "outsiders": "Outsiders",
    "minions": "Minions",
    "demons": "Demons",
}

SCRIPT_LABELS = {
    "trouble_brewing": "Trouble Brewing",
    "sects_and_violets": "Sects and Violets",
    "bad_moon_rising": "Bad Moon Rising",
    "experimental": "Experimental",
}

TYPE_INDEX_FILES = {
    "Townsfolk": "roles/types/townsfolk.md",
    "Outsiders": "roles/types/outsiders.md",
    "Minions": "roles/types/minions.md",
    "Demons": "roles/types/demons.md",
}

TYPE_INDEX_CONTENT = {
    "townsfolk": {
        "title": "Townsfolk",
        "filename": "townsfolk.md",
    },
    "outsiders": {
        "title": "Outsiders",
        "filename": "outsiders.md",
    },
    "minions": {
        "title": "Minions",
        "filename": "minions.md",
    },
    "demons": {
        "title": "Demons",
        "filename": "demons.md",
    },
}


def humanize_slug(slug: str) -> str:
    return slug.replace("_", " ").replace("-", " ").title()


def get_script_label(script_slug: str) -> str:
    return SCRIPT_LABELS.get(script_slug, humanize_slug(script_slug))


def get_role_label(file_path: Path) -> str:
    return humanize_slug(file_path.stem)


def discover_script_slugs() -> list[str]:
    """
    Discover canonical script slugs from docs/roles/, excluding helper dirs.
    Only include scripts that also have the matching new scripts/<slug>/ structure.
    """
    if not ROLES_DIR.exists():
        return []

    discovered: list[str] = []
    for child in ROLES_DIR.iterdir():
        if not child.is_dir():
            continue
        if child.name in EXCLUDED_ROLE_DIRS:
            continue

        script_slug = child.name
        role_index = child / "index.md"
        script_dir = SCRIPTS_DIR / script_slug
        script_index = script_dir / "index.md"
        script_overview = script_dir / "overview.md"

        if script_slug == "experimental":
            discovered.append(script_slug)
            continue

        if role_index.exists() and script_index.exists() and script_overview.exists():
            discovered.append(script_slug)

    preferred = [slug for slug in PREFERRED_SCRIPT_ORDER if slug in discovered]
    extras = sorted(slug for slug in discovered if slug not in PREFERRED_SCRIPT_ORDER)
    return preferred + extras


def discover_top_level_strategy_pages() -> list[Path]:
    strategy_dir = DOCS_DIR / "strategy"
    if not strategy_dir.exists():
        return []

    pages = [
        p for p in strategy_dir.glob("*.md")
        if p.is_file() and p.name.lower() != "index.md"
    ]
    return sorted(pages, key=lambda p: humanize_slug(p.stem))


def build_strategy_list_block() -> str:
    lines: list[str] = [STRATEGY_PAGE_START_MARKER, ""]

    pages = discover_top_level_strategy_pages()
    if pages:
        for page in pages:
            label = humanize_slug(page.stem)
            rel_path = page.name
            lines.append(f"- [{label}]({rel_path})")
    else:
        lines.append("_Add links as pages are created._")

    lines.append("")
    lines.append(STRATEGY_PAGE_END_MARKER)
    return "\n".join(lines)


def update_strategy_index_files(write: bool, script_slugs: list[str]) -> list[str]:
    messages: list[str] = []

    # Top-level strategy index
    if STRATEGY_INDEX_FILE.exists():
        original = STRATEGY_INDEX_FILE.read_text(encoding="utf-8")
        replacement_block = build_strategy_list_block()

        try:
            updated = replace_between_markers(
                original,
                STRATEGY_PAGE_START_MARKER,
                STRATEGY_PAGE_END_MARKER,
                replacement_block,
            )
        except ValueError:
            messages.append(
                f"Missing markers in strategy index file: {STRATEGY_INDEX_FILE} "
                f"(expected {STRATEGY_PAGE_START_MARKER} / {STRATEGY_PAGE_END_MARKER})"
            )
        else:
            if write:
                STRATEGY_INDEX_FILE.write_text(updated, encoding="utf-8")
                messages.append(f"Updated {STRATEGY_INDEX_FILE}")
            else:
                messages.append(f"Would update {STRATEGY_INDEX_FILE}")
    else:
        messages.append(f"Missing strategy index file: {STRATEGY_INDEX_FILE}")

    # Per-script strategy index pages
    for script_slug in script_slugs:
        output_path = SCRIPTS_DIR / script_slug / "strategy" / "index.md"
        if not output_path.exists():
            continue

        original = output_path.read_text(encoding="utf-8")
        replacement_block = build_script_strategy_list_block(script_slug)

        try:
            updated = replace_between_markers(
                original,
                SCRIPT_STRATEGY_PAGE_START_MARKER,
                SCRIPT_STRATEGY_PAGE_END_MARKER,
                replacement_block,
            )
        except ValueError:
            messages.append(
                f"Missing markers in script strategy index file: {output_path} "
                f"(expected {SCRIPT_STRATEGY_PAGE_START_MARKER} / {SCRIPT_STRATEGY_PAGE_END_MARKER})"
            )
            continue

        if write:
            output_path.write_text(updated, encoding="utf-8")
            messages.append(f"Updated {output_path}")
        else:
            messages.append(f"Would update {output_path}")

    return messages


def check_strategy_index_files(script_slugs: list[str]) -> tuple[bool, list[str]]:
    messages: list[str] = []
    all_up_to_date = True

    # Top-level strategy index
    if STRATEGY_INDEX_FILE.exists():
        original = STRATEGY_INDEX_FILE.read_text(encoding="utf-8")
        replacement_block = build_strategy_list_block()

        try:
            expected = replace_between_markers(
                original,
                STRATEGY_PAGE_START_MARKER,
                STRATEGY_PAGE_END_MARKER,
                replacement_block,
            )
        except ValueError:
            all_up_to_date = False
            messages.append(
                f"Missing markers in strategy index file: {STRATEGY_INDEX_FILE} "
                f"(expected {STRATEGY_PAGE_START_MARKER} / {STRATEGY_PAGE_END_MARKER})"
            )
        else:
            if original != expected:
                all_up_to_date = False
                messages.append(f"Out of date: {STRATEGY_INDEX_FILE}")
    else:
        all_up_to_date = False
        messages.append(f"Missing strategy index file: {STRATEGY_INDEX_FILE}")

    # Per-script strategy index pages
    for script_slug in script_slugs:
        output_path = SCRIPTS_DIR / script_slug / "strategy" / "index.md"
        if not output_path.exists():
            continue

        original = output_path.read_text(encoding="utf-8")
        replacement_block = build_script_strategy_list_block(script_slug)

        try:
            expected = replace_between_markers(
                original,
                SCRIPT_STRATEGY_PAGE_START_MARKER,
                SCRIPT_STRATEGY_PAGE_END_MARKER,
                replacement_block,
            )
        except ValueError:
            all_up_to_date = False
            messages.append(
                f"Missing markers in script strategy index file: {output_path} "
                f"(expected {SCRIPT_STRATEGY_PAGE_START_MARKER} / {SCRIPT_STRATEGY_PAGE_END_MARKER})"
            )
            continue

        if original != expected:
            all_up_to_date = False
            messages.append(f"Out of date: {output_path}")

    return all_up_to_date, messages


def build_script_strategy_list_block(script_slug: str) -> str:
    lines: list[str] = [SCRIPT_STRATEGY_PAGE_START_MARKER, ""]

    pages = discover_strategy_pages(script_slug)
    if pages:
        for page in pages:
            label = humanize_slug(page.stem)
            rel_path = page.name
            lines.append(f"- [{label}]({rel_path})")
    else:
        lines.append("_Add links as pages are created._")

    lines.append("")
    lines.append(SCRIPT_STRATEGY_PAGE_END_MARKER)
    return "\n".join(lines)


def discover_role_pages(script_slug: str, role_type: str) -> list[Path]:
    folder = ROLES_DIR / script_slug / role_type
    if not folder.exists() or not folder.is_dir():
        return []

    pages = [
        p for p in folder.glob("*.md")
        if p.is_file() and p.name.lower() != "index.md"
    ]
    return sorted(pages, key=lambda p: get_role_label(p))


def indent(level: int) -> str:
    return "  " * level


def add_line(lines: list[str], level: int, text: str) -> None:
    lines.append(f"{indent(level)}{text}")


def replace_between_markers(
    text: str,
    start_marker: str,
    end_marker: str,
    replacement_block: str,
) -> str:
    start_idx = text.find(start_marker)
    end_idx = text.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        raise ValueError(
            f"Could not find markers:\n{start_marker}\n{end_marker}"
        )
    if end_idx < start_idx:
        raise ValueError(
            f"End marker appears before start marker:\n{start_marker}\n{end_marker}"
        )

    end_idx += len(end_marker)
    return text[:start_idx] + replacement_block + text[end_idx:]


def build_roles_section(lines: list[str], script_slugs: list[str], base_level: int = 1) -> None:
    add_line(lines, base_level, "- Roles:")
    add_line(lines, base_level + 1, "- Overview: roles/index.md")

    add_line(lines, base_level + 1, "- By Script:")
    for script_slug in script_slugs:
        script_label = get_script_label(script_slug)
        script_index = f"roles/{script_slug}/index.md"

        add_line(lines, base_level + 2, f"- {script_label}:")
        add_line(lines, base_level + 3, f"- Overview: {script_index}")

        for role_type in ROLE_TYPE_ORDER:
            role_type_label = ROLE_TYPE_LABELS[role_type]
            role_index = f"roles/{script_slug}/{role_type}/index.md"

            add_line(lines, base_level + 3, f"- {role_type_label}:")
            add_line(lines, base_level + 4, f"- Overview: {role_index}")

            for page in discover_role_pages(script_slug, role_type):
                rel_path = page.relative_to(DOCS_DIR).as_posix()
                role_label = get_role_label(page)
                add_line(lines, base_level + 4, f"- {role_label}: {rel_path}")

    add_line(lines, base_level + 1, "- By Type:")
    add_line(lines, base_level + 2, "- Overview: roles/types/index.md")
    for label, rel_path in TYPE_INDEX_FILES.items():
        add_line(lines, base_level + 2, f"- {label}: {rel_path}")


def discover_strategy_pages(script_slug: str) -> list[Path]:
    strategy_dir = SCRIPTS_DIR / script_slug / "strategy"
    if not strategy_dir.exists():
        return []

    pages = [
        p for p in strategy_dir.glob("*.md")
        if p.is_file() and p.name.lower() != "index.md"
    ]
    return sorted(pages, key=lambda p: humanize_slug(p.stem))


def build_scripts_section(lines: list[str], script_slugs: list[str], base_level: int = 1) -> None:
    add_line(lines, base_level, "- Scripts:")
    add_line(lines, base_level + 1, "- Overview: scripts/index.md")

    for script_slug in script_slugs:
        script_label = get_script_label(script_slug)
        script_base = f"scripts/{script_slug}"
        script_dir = SCRIPTS_DIR / script_slug

        has_index = (script_dir / "index.md").exists()
        has_overview = (script_dir / "overview.md").exists()
        has_strategy_dir = (script_dir / "strategy").exists()

        # Skip entries that do not actually have a script section yet.
        if not (has_index or has_overview or has_strategy_dir):
            continue

        add_line(lines, base_level + 1, f"- {script_label}:")

        if has_index:
            add_line(lines, base_level + 2, f"- Start Here: {script_base}/index.md")

        if has_overview:
            add_line(lines, base_level + 2, f"- Overview: {script_base}/overview.md")

        if has_strategy_dir:
            add_line(lines, base_level + 2, "- Strategy:")

            if (script_dir / "strategy" / "index.md").exists():
                add_line(lines, base_level + 3, f"- Overview: {script_base}/strategy/index.md")

            for page in discover_strategy_pages(script_slug):
                rel_path = page.relative_to(DOCS_DIR).as_posix()
                label = humanize_slug(page.stem)
                add_line(lines, base_level + 3, f"- {label}: {rel_path}")


def build_strategy_section(lines: list[str], base_level: int = 1) -> None:
    STRATEGY_DIR = DOCS_DIR / "strategy"

    if not STRATEGY_DIR.exists():
        return

    add_line(lines, base_level, "- Strategy:")
    add_line(lines, base_level + 1, "- Overview: strategy/index.md")

    # top-level guides (exclude index.md)
    pages = [
        p for p in STRATEGY_DIR.glob("*.md")
        if p.is_file() and p.name.lower() != "index.md"
    ]

    for page in sorted(pages, key=lambda p: humanize_slug(p.stem)):
        rel_path = page.relative_to(DOCS_DIR).as_posix()
        label = humanize_slug(page.stem)
        add_line(lines, base_level + 1, f"- {label}: {rel_path}")


def build_generated_nav_block(script_slugs: list[str]) -> str:
    lines: list[str] = [NAV_START_MARKER]
    build_roles_section(lines, script_slugs=script_slugs, base_level=1)
    lines.append("")
    build_scripts_section(lines, script_slugs=script_slugs, base_level=1)
    build_strategy_section(lines)
    lines.append(NAV_END_MARKER)
    return "\n".join(lines)


def build_type_role_list_block(role_type: str, script_slugs: list[str]) -> str:
    if role_type not in TYPE_INDEX_CONTENT:
        raise ValueError(f"Unsupported role type: {role_type}")

    lines: list[str] = [TYPE_PAGE_START_MARKER, ""]
    any_content = False

    for script_slug in script_slugs:
        pages = discover_role_pages(script_slug, role_type)
        if not pages:
            continue

        any_content = True
        lines.append(f"## {get_script_label(script_slug)}")
        lines.append("")

        for page in pages:
            role_label = get_role_label(page)
            rel_path = Path("..") / script_slug / role_type / page.name
            lines.append(f"- [{role_label}]({rel_path.as_posix()})")

        lines.append("")

    if not any_content:
        lines.append("_Add links as pages are created._")
        lines.append("")

    lines.append(TYPE_PAGE_END_MARKER)
    return "\n".join(lines)


def update_type_index_files(write: bool, script_slugs: list[str]) -> list[str]:
    messages: list[str] = []

    for role_type, meta in TYPE_INDEX_CONTENT.items():
        output_path = TYPES_DIR / meta["filename"]

        if not output_path.exists():
            messages.append(f"Missing type index file: {output_path}")
            continue

        original = output_path.read_text(encoding="utf-8")
        replacement_block = build_type_role_list_block(role_type, script_slugs)

        try:
            updated = replace_between_markers(
                original,
                TYPE_PAGE_START_MARKER,
                TYPE_PAGE_END_MARKER,
                replacement_block,
            )
        except ValueError:
            messages.append(
                f"Missing markers in type index file: {output_path} "
                f"(expected {TYPE_PAGE_START_MARKER} / {TYPE_PAGE_END_MARKER})"
            )
            continue

        if write:
            output_path.write_text(updated, encoding="utf-8")
            messages.append(f"Updated {output_path}")
        else:
            messages.append(f"Would update {output_path}")

    return messages


def check_type_index_files(script_slugs: list[str]) -> tuple[bool, list[str]]:
    messages: list[str] = []
    all_up_to_date = True

    for role_type, meta in TYPE_INDEX_CONTENT.items():
        output_path = TYPES_DIR / meta["filename"]

        if not output_path.exists():
            all_up_to_date = False
            messages.append(f"Missing type index file: {output_path}")
            continue

        original = output_path.read_text(encoding="utf-8")
        replacement_block = build_type_role_list_block(role_type, script_slugs)

        try:
            expected = replace_between_markers(
                original,
                TYPE_PAGE_START_MARKER,
                TYPE_PAGE_END_MARKER,
                replacement_block,
            )
        except ValueError:
            all_up_to_date = False
            messages.append(
                f"Missing markers in type index file: {output_path} "
                f"(expected {TYPE_PAGE_START_MARKER} / {TYPE_PAGE_END_MARKER})"
            )
            continue

        if original != expected:
            all_up_to_date = False
            messages.append(f"Out of date: {output_path}")

    return all_up_to_date, messages


def main() -> int:
    write = "--write" in sys.argv
    check = "--check" in sys.argv

    if write and check:
        print("Use either --write or --check, not both.", file=sys.stderr)
        return 2

    if not MKDOCS_FILE.exists():
        print(f"mkdocs.yml not found: {MKDOCS_FILE}", file=sys.stderr)
        return 1

    if not TYPES_DIR.exists():
        print(f"types directory not found: {TYPES_DIR}", file=sys.stderr)
        return 1

    script_slugs = discover_script_slugs()

    original = MKDOCS_FILE.read_text(encoding="utf-8")
    generated_block = build_generated_nav_block(script_slugs)

    try:
        updated = replace_between_markers(
            original,
            NAV_START_MARKER,
            NAV_END_MARKER,
            generated_block,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if check:
        ok = True

        if original != updated:
            print("mkdocs.yml nav block is out of date.", file=sys.stderr)
            ok = False

        types_ok, type_messages = check_type_index_files(script_slugs)
        if not types_ok:
            ok = False
            for msg in type_messages:
                print(msg, file=sys.stderr)

        strategy_ok, strategy_messages = check_strategy_index_files(script_slugs)
        if not strategy_ok:
            ok = False
            for msg in strategy_messages:
                print(msg, file=sys.stderr)

        if ok:
            print("mkdocs.yml nav block and type index pages are up to date.")
            return 0
        return 1

    if write:
        MKDOCS_FILE.write_text(updated, encoding="utf-8")
        print(f"Updated nav block in {MKDOCS_FILE}")

        for msg in update_type_index_files(write=True, script_slugs=script_slugs):
            print(msg)

        for msg in update_strategy_index_files(write=True, script_slugs=script_slugs):
            print(msg)

        return 0

    print(generated_block)
    print()
    for msg in update_type_index_files(write=False, script_slugs=script_slugs):
        print(msg)
    for msg in update_strategy_index_files(write=False, script_slugs=script_slugs):
        print(msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())