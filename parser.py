import csv
import os
from collections import defaultdict

def process_csv_and_save(file_path):
    # Dictionary to store lists for each main location key
    location_data = defaultdict(lambda: defaultdict(list))
    output_dir = "out"

    try:
        with open(file_path, mode="r", encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile, delimiter=";")  # Use semicolon as delimiter
            header = next(reader)  # Skip the header row

            for row in reader:
                # Validate the row length to avoid index errors
                if len(row) > 5:
                    location_field = row[5].strip()  # Clean up whitespace

                    # Skip rows where the field contains "Lokalita"
                    if "Lokalita" not in location_field:
                        # Split location field into main key and sub key
                        location_parts = location_field.split("/")
                        main_key = location_parts[0].strip()

                        if len(location_parts) > 1:
                            sub_key = location_parts[1].strip()
                            # Extract data for the current row
                            inventarni_cislo = row[0].strip()  # Index 0
                            nazev = row[1].strip()  # Index 1
                            # Store data in nested structure
                            location_data[main_key][sub_key].append((inventarni_cislo, nazev))

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Save data to files
        for main_key, sub_dict in location_data.items():
            main_folder = os.path.join(output_dir, main_key)
            os.makedirs(main_folder, exist_ok=True)

            for sub_key, items in sub_dict.items():
                file_name = f"{sub_key}.csv"  # Sub-location as file name
                file_path = os.path.join(main_folder, file_name)
                with open(file_path, mode="w", encoding="utf-8", newline="") as csvfile:
                    writer = csv.writer(csvfile, delimiter=";", quoting=csv.QUOTE_NONE, escapechar='\\')

                    # Write informational first line with the additional message
                    writer.writerow([f"{main_key}/{sub_key}", f"Místnost: {main_key}/{sub_key}", ""])

                    # Write all the data
                    for inventarni_cislo, nazev in items:
                        writer.writerow([f"{inventarni_cislo}", "", "", f"{nazev}"])

        # Print statistics
        print("\nStatistics:")
        for main_key, sub_dict in location_data.items():
            main_count = sum(len(items) for items in sub_dict.values())
            print(f"{main_key}: {main_count} items")
            for sub_key, items in sub_dict.items():
                print(f"\t{sub_key}: {len(items)} items")

        print(f"\nAll data successfully saved to the '{output_dir}' directory.")

    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Specify the path to the CSV file
    file_path = "MANKO.csv"
    process_csv_and_save(file_path)