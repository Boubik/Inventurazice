import os
import csv
from collections import defaultdict

def create_nested_folder_structure(base_folder, sub_keys):
    """Creates nested folder structure for a list of sub-keys."""
    current_path = base_folder
    for sub_key in sub_keys[:-1]:  # Create folders for all but the last part
        current_path = os.path.join(current_path, sub_key)
        os.makedirs(current_path, exist_ok=True)
    return current_path


def process_and_save_by_rooms(file_path, output_dir="out/rooms"):
    location_data = defaultdict(lambda: defaultdict(list))
    total_items = 0

    try:
        with open(file_path, mode="r", encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile, delimiter=";")
            next(reader)  # Skip the header row

            for row in reader:
                if len(row) > 5:
                    location_field = row[5].strip()

                    if "Lokalita" not in location_field:
                        location_parts = location_field.split("/")
                        main_key = location_parts[0].strip()
                        sub_keys = [part.strip() for part in location_parts[1:]]

                        if len(location_parts) > 1:
                            sub_key = location_parts[1].strip()
                            # Extract data for the current row
                            inventarni_cislo = row[0].strip()  # Index 0
                            nazev = row[1].strip()  # Index 1
                            # Store data in nested structure
                            location_data[main_key][sub_key].append((inventarni_cislo, nazev))
                            total_items += 1  # Increment the total items counter

        os.makedirs(output_dir, exist_ok=True)

        for main_key, sub_dict in location_data.items():
            main_folder = os.path.join(output_dir, main_key)
            os.makedirs(main_folder, exist_ok=True)

            for sub_keys, items in sub_dict.items():
                # Create nested folder structure for sub-keys
                sub_folder = create_nested_folder_structure(main_folder, sub_keys)
                # The last part of sub_keys is used as the file name
                file_name = f"{sub_keys[-1]}.csv"
                file_path = os.path.join(sub_folder, file_name)
                with open(file_path, mode="w", encoding="utf-8", newline="") as csvfile:
                    writer = csv.writer(csvfile, delimiter=";", quoting=csv.QUOTE_NONE, escapechar='\\')
                    writer.writerow([f"{main_key}/{'/'.join(sub_keys)}", f"Místnost: {main_key}/{'/'.join(sub_keys)}", ""])
                    for inventarni_cislo, nazev in items:
                        writer.writerow([f"{inventarni_cislo}", "", f"{nazev}"])

        print("\nStatistics:")
        for main_key, sub_dict in location_data.items():
            main_count = sum(len(items) for items in sub_dict.values())
            print(f"{main_key}: {main_count} items")
            for sub_keys, items in sub_dict.items():
                print(f"\t{'/'.join(sub_keys)}: {len(items)} items")

        # Print total statistics
        print(f"\nTotal items across all locations: {total_items}")
        print(f"All data successfully saved to the '{output_dir}' directory.")

    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


def process_and_save_by_owner(file_path, output_dir="out/names"):
    owner_data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    total_items = 0

    try:
        with open(file_path, mode="r", encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile, delimiter=";")
            owner = None

            for row in reader:
                if len(row) > 0:
                    first_col = row[0].strip()

                    if first_col.lower().startswith("odpovědná ososba:"):
                        owner = first_col.replace("Odpovědná ososba:", "").strip()
                        print(f"Detected owner: {owner}")
                        next(reader, None)
                        next(reader, None)
                    elif owner and len(row) > 5:
                        location_field = row[5].strip()

                        if "Lokalita" not in location_field:
                            location_parts = location_field.split("/")
                            main_key = location_parts[0].strip()
                            sub_keys = [part.strip() for part in location_parts[1:]]

                            if len(sub_keys) > 0:
                                inventarni_cislo = row[0].strip()
                                nazev = row[1].strip()
                                owner_data[owner][main_key][tuple(sub_keys)].append((inventarni_cislo, nazev))
                                total_items += 1

        os.makedirs(output_dir, exist_ok=True)

        for owner, locations in owner_data.items():
            owner_folder = os.path.join(output_dir, owner)
            os.makedirs(owner_folder, exist_ok=True)

            for main_key, sub_dict in locations.items():
                main_folder = os.path.join(owner_folder, main_key)
                os.makedirs(main_folder, exist_ok=True)

                for sub_keys, items in sub_dict.items():
                    # Create nested folder structure for sub-keys
                    sub_folder = create_nested_folder_structure(main_folder, sub_keys)
                    # The last part of sub_keys is used as the file name
                    file_name = f"{sub_keys[-1]}.csv"
                    file_path = os.path.join(sub_folder, file_name)
                    with open(file_path, mode="w", encoding="utf-8", newline="") as csvfile:
                        writer = csv.writer(csvfile, delimiter=";", quoting=csv.QUOTE_NONE, escapechar='\\')
                        writer.writerow([f"{main_key}/{'/'.join(sub_keys)}", f"Místnost: {main_key}/{'/'.join(sub_keys)}", ""])
                        for inventarni_cislo, nazev in items:
                            writer.writerow([f"{inventarni_cislo}", "", f"{nazev}"])

        print("\nStatistics by owner:")
        for owner, locations in owner_data.items():
            print(f"{owner}:")
            for main_key, sub_dict in locations.items():
                main_count = sum(len(items) for items in sub_dict.values())
                print(f"\t{main_key}: {main_count} items")
                for sub_keys, items in sub_dict.items():
                    print(f"\t\t{'/'.join(sub_keys)}: {len(items)} items")

        print(f"\nTotal items across all owners and locations: {total_items}")
        print(f"All data successfully saved to the '{output_dir}' directory.")

    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    # Specify the path to the CSV file
    file_path = "MANKO.csv"
    output_dir_by_rooms = "out/rooms"
    output_dir_by_owner = "out/names"
    print("Processing data by locations...")
    process_and_save_by_rooms(file_path, output_dir_by_rooms)
    print("\nProcessing data by owners...")
    process_and_save_by_owner(file_path, output_dir_by_owner)