from __future__ import annotations

import argparse
import csv
import glob
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

ROOM_HEADER_PREFIXES = ("místnost:", "mistnost:")
OWNER_PREFIXES = (
    "odpovědná osoba:",
    "odpovedna osoba:",
    "odpovědná ososba:",  # typo used by the current MANKO export
    "odpovedna ososba:",
)
SOURCE_ROOM = "room"
SOURCE_MANKO = "manko"


@dataclass(frozen=True)
class Record:
    inventory_id: str
    name: str
    owner: str
    room: str
    source: str = ""


@dataclass
class ImportStats:
    files_seen: int = 0
    files_recognized: int = 0
    files_skipped: int = 0
    rows_read: int = 0
    rows_skipped: int = 0
    exact_duplicates: int = 0
    merged_duplicates: int = 0
    conflicts: int = 0


@dataclass(frozen=True)
class ParsedFile:
    kind: str | None
    records: list[Record]


def clean(value: str | None) -> str:
    return (value or "").replace("\ufeff", "").strip()


def normalize_room(value: str) -> str:
    parts = [part.strip() for part in clean(value).replace("\\", "/").split("/") if part.strip()]
    return "/".join(parts)


def strip_owner_prefix(value: str) -> str | None:
    text = clean(value)
    folded = text.casefold()
    for prefix in OWNER_PREFIXES:
        if folded.startswith(prefix):
            return text[len(prefix):].strip()
    return None


def looks_like_room_export(first_row: Sequence[str], path: Path) -> bool:
    if not first_row:
        return False
    second = clean(first_row[1]).casefold() if len(first_row) > 1 else ""
    return second.startswith(ROOM_HEADER_PREFIXES) or path.name.casefold().startswith("evidencni_cisla_")


def looks_like_manko(rows: Sequence[Sequence[str]]) -> bool:
    for row in rows[:100]:
        if not row:
            continue
        if strip_owner_prefix(row[0]) is not None:
            return True
        if len(row) > 5 and clean(row[5]).casefold() == "lokalita":
            return True
    return False


def is_placeholder_location(value: str) -> bool:
    folded = clean(value).casefold()
    return not folded or folded == "lokalita" or folded.startswith("lokalita:")


def room_specificity(room: str) -> tuple[int, int]:
    room = normalize_room(room)
    return (room.count("/"), len(room))


def compatible_rooms(a: str, b: str) -> bool:
    a = normalize_room(a)
    b = normalize_room(b)
    if not a or not b:
        return True
    if a.casefold() == b.casefold():
        return True
    return a.casefold().endswith("/" + b.casefold()) or b.casefold().endswith("/" + a.casefold())


def resolve_row_room(fallback_room: str, row_room: str) -> str:
    """Prefer an explicit per-row room over the file-level search/header room.

    If one value is only a short alias of the other (7.06 vs 64/7.06), keep
    the more specific fully-qualified location.
    """
    fallback_room = normalize_room(fallback_room)
    row_room = normalize_room(row_room)

    if not row_room:
        return fallback_room
    if not fallback_room:
        return row_room
    if compatible_rooms(fallback_room, row_room):
        return max((fallback_room, row_room), key=room_specificity)
    return row_room


def parse_room_export(path: Path, rows: Sequence[Sequence[str]], stats: ImportStats) -> list[Record]:
    """Parse browser room exports.

    Old format:
      inventory;owner;name

    New format:
      inventory;owner;name;full_location

    The fourth column is optional and, when present, is authoritative for that
    row. This allows one browser export to contain multiple full locations.
    """
    if not rows:
        return []

    fallback_room = normalize_room(rows[0][0] if rows[0] else "")
    if len(rows[0]) > 1:
        description = clean(rows[0][1])
        if ":" in description and description.casefold().startswith(ROOM_HEADER_PREFIXES):
            described_room = normalize_room(description.split(":", 1)[1])
            if described_room and (
                not fallback_room or room_specificity(described_room) > room_specificity(fallback_room)
            ):
                fallback_room = described_room

    records: list[Record] = []
    for row in rows[1:]:
        stats.rows_read += 1
        if not row or all(not clean(value) for value in row):
            continue

        inventory_id = clean(row[0]) if row else ""
        if not inventory_id:
            stats.rows_skipped += 1
            continue

        owner = clean(row[1]) if len(row) > 1 else ""
        name = clean(row[2]) if len(row) > 2 else ""
        explicit_room = normalize_room(row[3]) if len(row) > 3 else ""
        room = resolve_row_room(fallback_room, explicit_room)

        if not room:
            stats.rows_skipped += 1
            print(f"[SKIP] {path}: inventory {inventory_id} has no room/location")
            continue

        records.append(Record(inventory_id, name, owner, room, str(path)))
    return records


def parse_manko(path: Path, rows: Sequence[Sequence[str]], stats: ImportStats) -> list[Record]:
    """Parse the official MANKO export.

    The current format stores:
      column 0 = inventory number
      column 1 = item name
      column 5 = full location (for example 64/7.06)
    and uses ``Odpovědná ososba: ...`` rows to start owner sections.
    """
    records: list[Record] = []
    owner = ""

    for row in rows:
        stats.rows_read += 1
        if not row or all(not clean(value) for value in row):
            continue

        first = clean(row[0]) if row else ""
        detected_owner = strip_owner_prefix(first)
        if detected_owner is not None:
            owner = detected_owner
            continue

        if len(row) <= 5:
            stats.rows_skipped += 1
            continue

        location = normalize_room(row[5])
        if is_placeholder_location(location):
            continue

        inventory_id = clean(row[0])
        name = clean(row[1])
        if not inventory_id or inventory_id.casefold() in {
            "inventární číslo",
            "inventarni cislo",
            "evidenční číslo",
            "evidencni cislo",
        }:
            continue

        records.append(Record(inventory_id, name, owner, location, str(path)))

    return records


def read_csv_rows(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        delimiter = ";"
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=";,\t,").delimiter
        except csv.Error:
            pass
        return list(csv.reader(handle, delimiter=delimiter))


def parse_file_typed(path: Path, stats: ImportStats) -> ParsedFile:
    stats.files_seen += 1
    try:
        rows = read_csv_rows(path)
    except (OSError, UnicodeError, csv.Error) as exc:
        stats.files_skipped += 1
        print(f"[SKIP] {path}: {exc}")
        return ParsedFile(None, [])

    first_nonempty = next((row for row in rows if row and any(clean(value) for value in row)), [])
    if not first_nonempty:
        stats.files_skipped += 1
        return ParsedFile(None, [])

    if looks_like_room_export(first_nonempty, path):
        stats.files_recognized += 1
        start = rows.index(first_nonempty)
        return ParsedFile(SOURCE_ROOM, parse_room_export(path, rows[start:], stats))

    if looks_like_manko(rows):
        stats.files_recognized += 1
        return ParsedFile(SOURCE_MANKO, parse_manko(path, rows, stats))

    stats.files_skipped += 1
    print(f"[SKIP] {path}: unknown CSV format")
    return ParsedFile(None, [])


def parse_file(path: Path, stats: ImportStats) -> list[Record]:
    """Compatibility wrapper returning records regardless of input kind."""
    return parse_file_typed(path, stats).records


def merge_duplicate(old: Record, new: Record, stats: ImportStats) -> Record:
    if (
        old.inventory_id.casefold() == new.inventory_id.casefold()
        and old.name == new.name
        and old.owner == new.owner
        and old.room.casefold() == new.room.casefold()
    ):
        stats.exact_duplicates += 1
        return old

    stats.merged_duplicates += 1

    room = old.room
    if compatible_rooms(old.room, new.room):
        if room_specificity(new.room) > room_specificity(old.room):
            room = new.room
    elif new.room and old.room:
        room = new.room
        stats.conflicts += 1
        print(
            f"[CONFLICT] {old.inventory_id}: room '{old.room}' ({old.source}) -> "
            f"'{new.room}' ({new.source}); using the later value"
        )
    elif new.room:
        room = new.room

    owner = new.owner or old.owner
    name = new.name or old.name
    if old.owner and new.owner and old.owner != new.owner:
        stats.conflicts += 1
    if old.name and new.name and old.name != new.name:
        stats.conflicts += 1

    return Record(old.inventory_id, name, owner, room, new.source or old.source)


def deduplicate(records: Iterable[Record], stats: ImportStats) -> list[Record]:
    by_inventory: dict[str, Record] = {}
    for record in records:
        key = clean(record.inventory_id).casefold()
        if not key:
            continue
        if key in by_inventory:
            by_inventory[key] = merge_duplicate(by_inventory[key], record, stats)
        else:
            by_inventory[key] = record
    return list(by_inventory.values())


def safe_segment(value: str) -> str:
    value = clean(value)
    value = re.sub(r'[<>:"/\\|?*]', "_", value)
    value = value.rstrip(" .")
    return value or "_unknown"


def room_output_path(base: Path, room: str) -> Path:
    parts = [safe_segment(part) for part in normalize_room(room).split("/") if part]
    if not parts:
        parts = ["_unknown"]
    return base.joinpath(*parts[:-1], f"{parts[-1]}.csv")


def natural_key(value: str) -> list[object]:
    return [int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", value)]


def reset_generated_csvs(folder: Path) -> None:
    if not folder.exists():
        return
    for csv_path in folder.rglob("*.csv"):
        csv_path.unlink()
    for directory in sorted((p for p in folder.rglob("*") if p.is_dir()), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            pass


def write_room_files(records: Iterable[Record], output_dir: Path) -> int:
    grouped: dict[str, list[Record]] = {}
    for record in records:
        room = normalize_room(record.room)
        if not room:
            continue
        grouped.setdefault(room, []).append(record)

    reset_generated_csvs(output_dir)
    for room, items in grouped.items():
        path = room_output_path(output_dir, room)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter=";", lineterminator="\n")
            writer.writerow([room, f"Místnost: {room}", ""])
            for item in sorted(items, key=lambda record: natural_key(record.inventory_id)):
                writer.writerow([item.inventory_id, item.owner, item.name])
    return len(grouped)


def write_owner_files(records: Iterable[Record], output_dir: Path) -> tuple[int, int]:
    grouped: dict[tuple[str, str], list[Record]] = {}
    owners: set[str] = set()
    for record in records:
        if not record.owner or not record.room:
            continue
        owners.add(record.owner)
        grouped.setdefault((record.owner, normalize_room(record.room)), []).append(record)

    reset_generated_csvs(output_dir)
    for (owner, room), items in grouped.items():
        owner_dir = output_dir / safe_segment(owner)
        path = room_output_path(owner_dir, room)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter=";", lineterminator="\n")
            writer.writerow([room, f"Místnost: {room}", ""])
            for item in sorted(items, key=lambda record: natural_key(record.inventory_id)):
                writer.writerow([item.inventory_id, owner, item.name])
    return len(owners), len(grouped)


def write_dataset(records: list[Record], output_root: Path) -> tuple[int, int, int]:
    rooms = write_room_files(records, output_root / "rooms")
    owners, owner_room_files = write_owner_files(records, output_root / "names")
    return rooms, owners, owner_room_files


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def expand_inputs(raw_inputs: Sequence[str], excluded_roots: Sequence[Path]) -> list[Path]:
    candidates: list[Path] = []
    if not raw_inputs:
        raw_inputs = ["."]

    for raw in raw_inputs:
        expanded = glob.glob(raw, recursive=True)
        if not expanded:
            expanded = [raw]
        for entry in expanded:
            path = Path(entry)
            if path.is_file() and path.suffix.casefold() == ".csv":
                candidates.append(path)
            elif path.is_dir():
                candidates.extend(path.rglob("*.csv"))

    unique: dict[str, Path] = {}
    for path in candidates:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if any(is_relative_to(resolved, root) for root in excluded_roots):
            continue
        if any(part.startswith(".") for part in path.parts if part not in (".", "..")):
            continue
        unique[str(resolved).casefold()] = path

    def sort_key(path: Path) -> tuple[float, str]:
        try:
            mtime = path.stat().st_mtime
        except OSError:
            mtime = 0.0
        return (mtime, str(path).casefold())

    return sorted(unique.values(), key=sort_key)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Parse inventory CSV exports. Room exports are written to out/rooms + out/names; "
            "official MANKO exports are kept separate in out/manko/rooms + out/manko/names."
        )
    )
    parser.add_argument(
        "inputs",
        metavar="INPUT",
        nargs="*",
        help="CSV file, directory, or glob. With no inputs, scan CSV files below the current directory.",
    )
    parser.add_argument("--output", default="out", help="Output root (default: out)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_root = Path(args.output)
    input_files = expand_inputs(args.inputs, [output_root])
    if not input_files:
        print("No input CSV files found. Nothing to do.")
        return 0

    print(f"Input files: {len(input_files)}")
    for path in input_files:
        print(f"  - {path}")

    stats = ImportStats()
    records_by_kind: dict[str, list[Record]] = {SOURCE_ROOM: [], SOURCE_MANKO: []}
    files_by_kind: dict[str, int] = {SOURCE_ROOM: 0, SOURCE_MANKO: 0}

    for path in input_files:
        parsed = parse_file_typed(path, stats)
        if parsed.kind in records_by_kind:
            files_by_kind[parsed.kind] += 1
            records_by_kind[parsed.kind].extend(parsed.records)

    print("\nOutputs:")

    if files_by_kind[SOURCE_ROOM]:
        room_records = deduplicate(records_by_kind[SOURCE_ROOM], stats)
        rooms, owners, owner_room_files = write_dataset(room_records, output_root)
        print(f"  Room exports ({files_by_kind[SOURCE_ROOM]} files):")
        print(f"    Unique inventory: {len(room_records)}")
        print(f"    Rooms written:    {rooms}")
        print(f"    Owners written:   {owners}")
        print(f"    Owner/room files: {owner_room_files}")
        print(f"    Path:             {output_root}")
    else:
        print("  Room exports: none (existing room output left untouched)")

    if files_by_kind[SOURCE_MANKO]:
        manko_records = deduplicate(records_by_kind[SOURCE_MANKO], stats)
        manko_root = output_root / "manko"
        rooms, owners, owner_room_files = write_dataset(manko_records, manko_root)
        print(f"  MANKO ({files_by_kind[SOURCE_MANKO]} files):")
        print(f"    Unique inventory: {len(manko_records)}")
        print(f"    Rooms written:    {rooms}")
        print(f"    Owners written:   {owners}")
        print(f"    Owner/room files: {owner_room_files}")
        print(f"    Path:             {manko_root}")
    else:
        print("  MANKO: none (existing MANKO output left untouched)")

    print("\nImport statistics:")
    print(f"  Files seen:          {stats.files_seen}")
    print(f"  Files recognized:    {stats.files_recognized}")
    print(f"  Files skipped:       {stats.files_skipped}")
    print(f"  Parsed rows:         {stats.rows_read}")
    print(f"  Exact duplicates:    {stats.exact_duplicates}")
    print(f"  Merged duplicates:   {stats.merged_duplicates}")
    print(f"  Conflicts:           {stats.conflicts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
