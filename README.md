# Inventory QR Code Viewer

A Python-based desktop application for generating and viewing QR codes for inventory items. This tool processes a CSV file containing inventory data, generates QR codes for each item (including room information), and displays them in a user-friendly interface—ideal for inventory tracking and management.

## Features

- **CSV File Support**: Handles inventory data with room names and item details.
- **Automatic QR Code Generation**: Creates QR codes for each item and corresponding rooms.
- **Detailed Item Display**:
  - Inventory Number (`Inventarizační číslo`)
  - Responsible Person (`Odpovědná osoba`)
  - Item Name (`Název`)
- **User-Friendly Navigation**:
  - Displays current position and total count (e.g., `64/3.41 - 1/73`)
  - Dark-themed, responsive interface

## Prerequisites

- Python 3.8 or later installed on your system.
- Required Python packages (see [Installation](#installation)).

# Installation

1. **Clone the Repository**:

	```bash
	git clone https://github.com/Boubik/Inventurazice.git
	cd Inventurazice
	```

2.	Set Up Virtual Environment (Optional but recommended):

	```bash
	python -m venv venv
	source venv/bin/activate   # On Windows: venv\Scripts\activate
	```

	3.	Install Required Packages:

	```bash
	pip install -r requirements.txt
	```


	4.	Place Your CSV File:
		•	Ensure your CSV file is in the inv folder (create this folder if it doesn’t exist).
		•	CSV Structure:

	```csv
	RoomName;RoomName
	Inventarizační číslo;Odpovědná osoba;Název
	001234567;John Doe;Office Desk
	001234568;Jane Smith;Chair
	```



# Usage

1.	Run the Application:

	```bash
	python run.py
	```


2.	Select a CSV File:
	•	The app will display available CSV files in the inv folder. Choose one to start.
3.	Navigate Through Items:
	•	Use the Next and Back buttons or the arrow keys (→ for next, ← for previous) to navigate through the items.
4.	View QR Codes:
	•	Each item will display:
	•	QR Code (based on Inventarizační číslo)
	•	Responsible Person (Odpovědná osoba)
	•	Item Name (Název)
	•	Room name and current position (e.g., 64/3.41 - 1/73)
5.	Exit or Return to Menu:
	•	Use the Escape key or the Menu button to return to the file selection screen.

# File Structure

```
inventory-qr-code-viewer/
├── inv/                       # Folder for CSV files
│   └── example.csv            # Example CSV file
├── run.py                     # Main application file
├── requirements.txt           # Python dependencies
└── README.md                  # Project documentation
```

# Dependencies

The required Python packages are listed in requirements.txt:
	•	tkinter (bundled with Python)
	•	qrcode
	•	pillow

# License

This project is licensed under the MIT License. See the LICENSE file for details.