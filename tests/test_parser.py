import csv
import tempfile
import unittest
from pathlib import Path

import parser as inventory_parser


class ParserTests(unittest.TestCase):
    def write_room_csv(self, path: Path, room: str, rows):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter=";")
            writer.writerow([room, f"Místnost: {room}", ""])
            writer.writerows(rows)

    def test_room_alias_prefers_fully_qualified_room_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "evidencni_cisla_7.06.csv"
            second = root / "evidencni_cisla_64_7.06.csv"
            rows = [
                ["1001", "Owner A", "Projector"],
                ["1002", "Owner B", "Computer"],
            ]
            self.write_room_csv(first, "7.06", rows)
            self.write_room_csv(second, "64/7.06", rows)

            stats = inventory_parser.ImportStats()
            records = []
            records.extend(inventory_parser.parse_file(first, stats))
            records.extend(inventory_parser.parse_file(second, stats))
            unique = inventory_parser.deduplicate(records, stats)

            self.assertEqual(2, len(unique))
            self.assertEqual({"64/7.06"}, {record.room for record in unique})
            self.assertEqual(2, stats.merged_duplicates)
            self.assertEqual(0, stats.conflicts)

    def test_repeated_run_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input.csv"
            out = root / "out"
            self.write_room_csv(
                source,
                "64/7.06",
                [
                    ["1001", "Owner A", "Projector"],
                    ["1001", "Owner A", "Projector"],
                    ["1002", "Owner B", "Computer"],
                ],
            )

            self.assertEqual(0, inventory_parser.main([str(source), "--output", str(out)]))
            room_file = out / "rooms" / "64" / "7.06.csv"
            first_bytes = room_file.read_bytes()

            self.assertEqual(0, inventory_parser.main([str(source), "--output", str(out)]))
            second_bytes = room_file.read_bytes()

            self.assertEqual(first_bytes, second_bytes)
            with room_file.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.reader(handle, delimiter=";"))
            self.assertEqual(3, len(rows))


if __name__ == "__main__":
    unittest.main()
