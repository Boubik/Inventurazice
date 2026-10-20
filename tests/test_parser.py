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

    def write_manko_csv(self, path: Path, owner: str, room: str, rows):
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter=";")
            writer.writerow([f"Odpovědná ososba: {owner}"])
            writer.writerow(["Inventární číslo", "Název předmětu", "Zařazeno", "Pořizovací cena", ".", "Lokalita", "NS"])
            writer.writerow([f"Umístění: CPTO Pasteurova/{room}"])
            for inventory_id, name in rows:
                writer.writerow([inventory_id, name, "", "", "", room, ""])

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

    def test_repeated_room_run_is_idempotent(self):
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

    def test_manko_and_room_exports_are_written_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            room_source = root / "evidencni_cisla_64_7.06.csv"
            manko_source = root / "MANKO.csv"
            out = root / "out"

            # Deliberately use the same inventory number in both datasets.
            self.write_room_csv(room_source, "64/7.06", [["1001", "Room Owner", "Room Projector"]])
            self.write_manko_csv(manko_source, "Manko Owner", "64/5.58", [["1001", "Manko Projector"]])

            self.assertEqual(
                0,
                inventory_parser.main([str(room_source), str(manko_source), "--output", str(out)]),
            )

            room_file = out / "rooms" / "64" / "7.06.csv"
            manko_file = out / "manko" / "rooms" / "64" / "5.58.csv"
            manko_owner_file = out / "manko" / "names" / "Manko Owner" / "64" / "5.58.csv"

            self.assertTrue(room_file.exists())
            self.assertTrue(manko_file.exists())
            self.assertTrue(manko_owner_file.exists())

            self.assertIn("Room Projector", room_file.read_text(encoding="utf-8"))
            self.assertNotIn("Manko Projector", room_file.read_text(encoding="utf-8"))
            self.assertIn("Manko Projector", manko_file.read_text(encoding="utf-8"))

    def test_processing_only_rooms_does_not_delete_existing_manko_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            room_source = root / "evidencni_cisla_64_7.06.csv"
            out = root / "out"
            sentinel = out / "manko" / "rooms" / "64" / "old.csv"
            sentinel.parent.mkdir(parents=True, exist_ok=True)
            sentinel.write_text("keep me", encoding="utf-8")
            self.write_room_csv(room_source, "64/7.06", [["1001", "Owner", "Projector"]])

            self.assertEqual(0, inventory_parser.main([str(room_source), "--output", str(out)]))
            self.assertEqual("keep me", sentinel.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
