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
                        writer.writerow([f"{inventarni_cislo}", "", f"{nazev}"])

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

def process_csv_by_owner(file_path):
    # Dictionary to store data by owner and location
    owner_data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    output_dir = "out/names"
    total_items = 0  # Initialize a counter for total items

    try:
        with open(file_path, mode="r", encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile, delimiter=";")
            owner = None

            for row in reader:
                # Skip empty rows
                if len(row) == 0:
                    continue

                # Process the first column of the current row
                first_col = row[0].strip()

                # Check for "Odpovědná osoba:"
                if first_col.lower().startswith("odpovědná ososba:"):  # Fix typo in "ososba"
                    owner = first_col.replace("Odpovědná ososba:", "").strip()
                    #print(f"Detected owner: {owner}")
                    # Skip two lines (header and metadata after owner)
                    next(reader, None)
                    next(reader, None)
                elif owner and len(row) > 5:  # Ensure valid data row
                    location_field = row[5].strip()

                    if "Lokalita" not in location_field:
                        location_parts = location_field.split("/")
                        main_key = location_parts[0].strip()

                        if len(location_parts) > 1:
                            sub_key = location_parts[1].strip()
                            inventarni_cislo = row[0].strip()
                            nazev = row[1].strip()
                            owner_data[owner][main_key][sub_key].append((inventarni_cislo, nazev))
                            total_items += 1
                        #else:
                            #print(f"Invalid location format in row: {row}")
                    #else:
                        #print(f"Skipped 'Lokalita' row: {row}")

        # Output directory structure
        os.makedirs(output_dir, exist_ok=True)

        for owner, locations in owner_data.items():
            owner_folder = os.path.join(output_dir, owner)
            os.makedirs(owner_folder, exist_ok=True)

            for main_key, sub_dict in locations.items():
                main_folder = os.path.join(owner_folder, main_key)
                os.makedirs(main_folder, exist_ok=True)

                for sub_key, items in sub_dict.items():
                    file_name = f"{sub_key}.csv"
                    file_path = os.path.join(main_folder, file_name)
                    with open(file_path, mode="w", encoding="utf-8", newline="") as csvfile:
                        writer = csv.writer(csvfile, delimiter=";", quoting=csv.QUOTE_NONE, escapechar='\\')
                        writer.writerow([f"{main_key}/{sub_key}", f"Místnost: {main_key}/{sub_key}", ""])
                        for inventarni_cislo, nazev in items:
                            writer.writerow([f"{inventarni_cislo}", owner, f"{nazev}"])

        print("\nStatistics by owner:")
        for owner, locations in owner_data.items():
            print(f"{owner}:")
            for main_key, sub_dict in locations.items():
                main_count = sum(len(items) for items in sub_dict.values())
                print(f"\t{main_key}: {main_count} items")
                for sub_key, items in sub_dict.items():
                    print(f"\t\t{sub_key}: {len(items)} items")

        print(f"\nTotal items across all owners and locations: {total_items}")
        print(f"All data successfully saved to the '{output_dir}' directory.")

    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Specify the path to the CSV file
    file_path = "MANKO.csv"
    print("Processing data by locations...")
    process_csv_and_save(file_path)
    print("\nProcessing data by owners...")
    process_csv_by_owner(file_path)