import csv
import qrcode
import tkinter as tk
from PIL import Image, ImageTk

# Function to load data from CSV with semicolon separator
def load_data(csv_file="evidencni_cisla_names.csv"):
    evidence_entries = []
    with open(csv_file, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')  # Use ';' as the delimiter
        for row in reader:
            evidencni_cislo, name = row[0].strip(), row[1].strip()
            evidence_entries.append((evidencni_cislo, name))
    return evidence_entries

# Function to generate QR code in memory
def generate_qr_image(evidencni_cislo):
    qr = qrcode.make(evidencni_cislo)
    return qr

# GUI class for displaying QR codes
class QRCodeViewer:
    def __init__(self, root, evidence_entries):
        self.root = root
        self.evidence_entries = evidence_entries
        self.index = 0

        # Configure root window
        self.root.title("QR Code Viewer")
        self.root.geometry("300x450")

        # Display widgets
        self.label_code = tk.Label(self.root, text="", font=("Arial", 14))
        self.label_code.pack(pady=5)
        
        self.qr_label = tk.Label(self.root)
        self.qr_label.pack(pady=10)

        self.label_name = tk.Label(self.root, text="", font=("Arial", 12, "italic"))
        self.label_name.pack(pady=5)

        # Navigation buttons
        self.back_button = tk.Button(self.root, text="Back", command=self.show_previous)
        self.back_button.pack(side="left", padx=20, pady=10)

        self.next_button = tk.Button(self.root, text="Next", command=self.show_next)
        self.next_button.pack(side="right", padx=20, pady=10)

        # Bind Enter, Right Arrow for Next; Left Arrow for Back
        self.root.bind("<Return>", lambda event: self.show_next())
        self.root.bind("<Right>", lambda event: self.show_next())
        self.root.bind("<Left>", lambda event: self.show_previous())

        # Show the first QR code
        self.show_qr_code()

    def show_qr_code(self):
        evidencni_cislo, name = self.evidence_entries[self.index]
        self.label_code.config(text=evidencni_cislo)
        self.label_name.config(text=name)

        # Generate the QR code image in memory
        qr_image = generate_qr_image(evidencni_cislo).resize((200, 200))
        self.qr_image_tk = ImageTk.PhotoImage(qr_image)
        self.qr_label.config(image=self.qr_image_tk)

    def show_next(self):
        # Move to the next entry
        self.index = (self.index + 1) % len(self.evidence_entries)
        self.show_qr_code()

    def show_previous(self):
        # Move to the previous entry
        self.index = (self.index - 1) % len(self.evidence_entries)
        self.show_qr_code()

# Load evidence entries from CSV
evidence_entries = load_data()

# Initialize and run the GUI
root = tk.Tk()
app = QRCodeViewer(root, evidence_entries)
root.mainloop()
