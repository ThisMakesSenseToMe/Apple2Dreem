import csv
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

from Apple2Dreem import SkipProcessing, process_file


FROM_DATE = datetime(2025, 1, 1, 19, 0, tzinfo=timezone.utc)
TO_DATE = datetime(2025, 1, 2, 11, 0, tzinfo=timezone.utc)
FIXTURES = Path(__file__).parent / "fixtures"


class ConversionTests(unittest.TestCase):
    def test_anonymized_multi_night_export_matches_golden_files(self):
        input_file = FIXTURES / "multi_night_health_export.json"
        expected_directory = FIXTURES / "expected"

        with tempfile.TemporaryDirectory() as directory:
            output_directory = Path(directory)
            process_file(
                str(input_file),
                str(output_directory),
                datetime(2025, 1, 1, 19, 0, tzinfo=timezone.utc),
                datetime(2025, 1, 3, 11, 0, tzinfo=timezone.utc),
                time_shift_seconds=0,
                input_type="json",
                rename=False,
            )

            generated_files = {
                path.name: path
                for path in output_directory.glob("Apple2Dreem_*.csv")
            }
            expected_files = {
                path.name: path
                for path in expected_directory.glob("Apple2Dreem_*.csv")
            }
            self.assertEqual(generated_files.keys(), expected_files.keys())

            for file_name, expected_file in expected_files.items():
                with self.subTest(file_name=file_name):
                    self.assertEqual(
                        self.read_csv_rows(generated_files[file_name]),
                        self.read_csv_rows(expected_file),
                    )

    def test_json_conversion_preserves_adjacent_sleep_stages(self):
        entries = [
            self.json_entry("Core", "22:00:00", "22:01:00"),
            self.json_entry("Deep", "22:01:00", "22:02:00"),
            self.json_entry("REM", "22:02:00", "22:02:30"),
        ]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_file = root / "HealthAutoExport-test.json"
            input_file.write_text(
                json.dumps({"data": {"metrics": [{"data": entries}]}}),
                encoding="utf-8",
            )

            process_file(
                str(input_file),
                str(root),
                FROM_DATE,
                TO_DATE,
                time_shift_seconds=0,
                input_type="json",
                rename=False,
            )

            row = self.read_output_row(root)
            self.assertEqual(row["Start Time"], "2025-01-01T22:00:00")
            self.assertEqual(row["Stop Time"], "2025-01-01T22:02:30")
            self.assertEqual(row["Sleep Duration"], "0:02:30")
            self.assertEqual(row["Light Sleep Duration"], "0:01:00")
            self.assertEqual(row["Deep Sleep Duration"], "0:01:00")
            self.assertEqual(row["REM Duration"], "0:00:30")
            self.assertEqual(row["Hypnogram"], "[Light,Light,Deep,Deep,REM]")

    def test_csv_zip_conversion_maps_stages_and_separator_line(self):
        csv_header = "type,sourceName,sourceVersion,productType,device,startDate,endDate,value,HKTimeZone"
        first_csv = "\n".join(
            [
                "sep=,",
                csv_header,
                "Sleep Analysis,Apple Watch,,,,2025-01-01T22:00:00Z,2025-01-01T22:00:30Z,awake,UTC",
                "Sleep Analysis,Apple Watch,,,,2025-01-01T22:00:30Z,2025-01-01T22:01:30Z,asleepCore,UTC",
            ]
        )
        second_csv = "\n".join(
            [
                csv_header,
                "Sleep Analysis,Apple Watch,,,,2025-01-01T22:01:30Z,2025-01-01T22:02:00Z,asleepREM,UTC",
            ]
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_file = root / "health-export.zip"
            with ZipFile(input_file, "w") as archive:
                archive.writestr("SleepAnalysis-part1.csv", first_csv)
                archive.writestr("SleepAnalysis-part2.csv", second_csv)
                archive.writestr(
                    "HeartRate.csv",
                    "\n".join(
                        [
                            csv_header,
                            "Heart Rate,Apple Watch,,,,2025-01-01T22:02:00Z,2025-01-01T22:03:00Z,72,UTC",
                        ]
                    ),
                )
                archive.writestr("README.txt", "not health data")

            process_file(
                str(input_file),
                str(root),
                FROM_DATE,
                TO_DATE,
                time_shift_seconds=0,
                input_type="csv",
                rename=False,
            )

            row = self.read_output_row(root)
            self.assertEqual(row["Sleep Onset Duration"], "0:00:30")
            self.assertEqual(row["Light Sleep Duration"], "0:01:00")
            self.assertEqual(row["REM Duration"], "0:00:30")
            self.assertEqual(row["Wake After Sleep Onset Duration"], "0:00:00")
            self.assertEqual(row["Hypnogram"], "[WAKE,Light,Light,REM]")

    def test_json_conversion_requires_source_selection_for_multiple_sources(self):
        entries = [
            self.json_entry("Core", "22:00:00", "22:01:00", source="Watch A"),
            self.json_entry("Deep", "22:00:00", "22:01:00", source="Watch B"),
        ]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_file = root / "HealthAutoExport-sources.json"
            input_file.write_text(
                json.dumps({"data": {"metrics": [{"data": entries}]}}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(SkipProcessing, "Multiple sources detected"):
                process_file(
                    str(input_file),
                    str(root),
                    FROM_DATE,
                    TO_DATE,
                    time_shift_seconds=0,
                    input_type="json",
                    rename=False,
                )

            process_file(
                str(input_file),
                str(root),
                FROM_DATE,
                TO_DATE,
                time_shift_seconds=0,
                input_type="json",
                rename=False,
                use_source="Watch B",
            )

            row = self.read_output_row(root)
            self.assertEqual(row["Deep Sleep Duration"], "0:01:00")
            self.assertEqual(row["Light Sleep Duration"], "0:00:00")
            self.assertEqual(row["Hypnogram"], "[Deep,Deep]")

    @staticmethod
    def json_entry(stage, start_time, end_time, source="Apple Watch"):
        return {
            "source": source,
            "qty": 1.0,
            "startDate": f"2025-01-01T{start_time}+00:00",
            "endDate": f"2025-01-01T{end_time}+00:00",
            "value": stage,
        }

    def read_output_row(self, directory):
        output_files = list(directory.glob("Apple2Dreem_*.csv"))
        self.assertEqual(len(output_files), 1)
        rows = self.read_csv_rows(output_files[0])
        self.assertEqual(len(rows), 1)
        return rows[0]

    @staticmethod
    def read_csv_rows(file_path):
        with file_path.open(encoding="utf-8", newline="") as output:
            return list(csv.DictReader(output, delimiter=";"))


if __name__ == "__main__":
    unittest.main()
