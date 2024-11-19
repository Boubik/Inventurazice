import csv
import qrcode
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from PIL import Image, ImageTk
import os

# Function to load data from CSV
def load_data(csv_file):
    evidence_entries = []
    room_name = ""
    try:
        with open(csv_file, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile, delimiter=';')
            room_name = next(reader)[0].strip()  # First line contains the room name
            evidence_entries.append((room_name, room_name, room_name))  # Add room as its own QR entry
            for row in reader:
                try:
                    # Parse three values: Inventarizační číslo, Owner, Name
                    inventarizacni_cislo = row[0].strip()
                    owner = row[1].strip()
                    name = row[2].strip()
                    evidence_entries.append((inventarizacni_cislo, owner, name))
                except IndexError:
                    continue  # Skip malformed rows
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load data from {csv_file}:\n{str(e)}")
    return room_name, evidence_entries

# Function to generate QR code
def generate_qr_image(content):
    qr = qrcode.make(content)
    return qr

# Main application class
class InventoryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory QR Code Viewer")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)

        # Set dark theme
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#2d2d2d")
        style.configure("TLabel", background="#2d2d2d", foreground="#ffffff")
        style.configure("TButton", background="#3e3e3e", foreground="#ffffff", font=("Arial", 10, "bold"), padding=5)
        style.map("TButton", background=[("active", "#4f4f4f")])

        # Folder Path
        self.folder_path = "inv"
        if not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path)

        # Initialize views
        self.file_selection_view()

    def clear_view(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def file_selection_view(self):
        self.clear_view()

        # Main frame
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title label
        ttk.Label(main_frame, text="Select a CSV File", font=("Arial", 16)).pack(pady=10, anchor="w")

        # Listbox with scrollbar
        listbox_frame = ttk.Frame(main_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        self.file_listbox = tk.Listbox(listbox_frame, font=("Arial", 12), activestyle="none", bg="#3e3e3e", fg="#ffffff", selectbackground="#4f4f4f")
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.file_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=scrollbar.set)

        # Populate listbox
        self.refresh_file_list()

        # Buttons (Centered)
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        button_frame.columnconfigure(0, weight=1)

        ttk.Button(button_frame, text="Refresh", command=self.refresh_file_list).grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        ttk.Button(button_frame, text="Open", command=self.open_file).grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        # Bind double-click and enter for file selection
        self.file_listbox.bind("<Double-1>", lambda event: self.open_file())
        self.root.bind("<Return>", lambda event: self.open_selected_file())

    def refresh_file_list(self):
        self.file_listbox.delete(0, tk.END)
        self.csv_files = [f for f in os.listdir(self.folder_path) if f.endswith('.csv')]
        if not self.csv_files:
            messagebox.showwarning("No Files", "No CSV files found in the folder.")
        else:
            for file in self.csv_files:
                self.file_listbox.insert(tk.END, file)
            # Auto-select the first file
            self.file_listbox.selection_set(0)

    def open_selected_file(self):
        selected_index = self.file_listbox.curselection()
        if selected_index:
            self.open_file()

    def open_file(self):
        selected_index = self.file_listbox.curselection()
        if not selected_index:
            messagebox.showwarning("No Selection", "Please select a file.")
            return

        selected_file = self.csv_files[selected_index[0]]
        file_path = os.path.join(self.folder_path, selected_file)

        room_name, evidence_entries = load_data(file_path)
        if evidence_entries:
            self.qr_code_viewer(room_name, evidence_entries)

    def qr_code_viewer(self, room_name, evidence_entries):
        self.clear_view()
        self.room_name = room_name
        self.evidence_entries = evidence_entries
        self.index = 0

        # Main frame
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # QR code position and room name display (Centered)
        self.position_label = ttk.Label(main_frame, text="", font=("Arial", 12))
        self.position_label.pack(pady=5)

        # Inventarizační číslo display (Centered)
        self.label_code = ttk.Label(main_frame, text="", font=("Arial", 14, "bold"), anchor="center")
        self.label_code.pack(pady=5)

        # QR code display (Centered)
        self.qr_label = ttk.Label(main_frame)
        self.qr_label.pack(pady=10)

        # Owner and Name display (Centered)
        self.label_owner = ttk.Label(main_frame, text="", font=("Arial", 12), anchor="center")
        self.label_owner.pack(pady=5)

        self.label_name = ttk.Label(main_frame, text="", font=("Arial", 12, "italic"), anchor="center")
        self.label_name.pack(pady=5)

        # Buttons (Centered)
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        button_frame.columnconfigure(0, weight=1)

        ttk.Button(button_frame, text="Back", command=self.show_previous).grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        ttk.Button(button_frame, text="Menu", command=self.file_selection_view).grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        ttk.Button(button_frame, text="Next", command=self.show_next).grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        # Bind keys for navigation and menu
        self.root.bind("<Right>", lambda event: self.show_next())
        self.root.bind("<Left>", lambda event: self.show_previous())
        self.root.bind("<Escape>", lambda event: self.file_selection_view())

        self.show_qr_code()

    def show_qr_code(self):
        inventarizacni_cislo, owner, name = self.evidence_entries[self.index]
        self.label_code.config(text=f"{inventarizacni_cislo}")
        self.label_owner.config(text=f"{owner}")
        self.label_name.config(text=f"{name}")

        qr_image = generate_qr_image(inventarizacni_cislo).resize((300, 300))
        self.qr_image_tk = ImageTk.PhotoImage(qr_image)
        self.qr_label.config(image=self.qr_image_tk)

        # Update position label with room name and counter
        self.position_label.config(text=f"{self.room_name} - {self.index + 1}/{len(self.evidence_entries)}")

    def show_next(self):
        if self.index < len(self.evidence_entries) - 1:
            self.index += 1
            self.show_qr_code()

    def show_previous(self):
        if self.index > 0:
            self.index -= 1
            self.show_qr_code()

# Run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = InventoryApp(root)
    root.mainloop()