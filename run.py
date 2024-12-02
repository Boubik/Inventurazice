import csv
import qrcode
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from PIL import Image, ImageTk
import os
import unicodedata

removeCZChars = True

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

def remove_accents(input_str):
    """
    Remove accents from a string.
    """
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([char for char in nfkd_form if not unicodedata.combining(char)])

# Main application class
class InventoryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory QR Code Viewer")
        self.root.geometry("800x700")
        self.root.minsize(600, 600)

        # Set dark theme
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#2d2d2d")
        style.configure("TLabel", background="#2d2d2d", foreground="#ffffff")
        style.configure("TButton", background="#3e3e3e", foreground="#ffffff", font=("Arial", 10, "bold"), padding=5)
        style.map("TButton", background=[("active", "#4f4f4f")])

        # Current folder path
        self.current_path = os.getcwd()  # Start in the root directory
        self.program_root = self.current_path  # Set program root directory

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

        # Current path label
        relative_path = os.path.relpath(self.current_path, self.program_root)
        self.current_path_label = ttk.Label(main_frame, text=f"Current Path: {relative_path}", font=("Arial", 12, "italic"))
        self.current_path_label.pack(pady=5, anchor="w")

        # Title label
        ttk.Label(main_frame, text="Select a CSV File", font=("Arial", 16)).pack(pady=10, anchor="w")

        # Search bar frame
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=5)
        ttk.Label(search_frame, text="Search: ").pack(side=tk.LEFT, padx=5)

        self.search_var = tk.StringVar()  # Variable to store search input
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.search_entry.configure(state="disabled")  # Initially disabled to avoid direct focus

        ttk.Button(search_frame, text="Search", command=self.perform_search).pack(side=tk.LEFT, padx=5)

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

        # Bind keys for search, navigation, and going back
        self.file_listbox.bind("<Key>", self.listbox_keypress)  # Capture alphanumeric keys for search
        self.file_listbox.bind("<BackSpace>", self.delete_from_search)  # Handle Backspace for deleting search
        self.file_listbox.bind("<Up>", lambda event: self.navigate_listbox(-1))
        self.file_listbox.bind("<Down>", lambda event: self.navigate_listbox(1))
        self.file_listbox.bind("<Return>", lambda event: self.open_file())  # Open selected item
        self.file_listbox.bind("<Escape>", lambda event: self.go_back())  # Go back in directories
        self.file_listbox.bind("<Double-1>", lambda event: self.open_selected_file())  # Fix for double-click to open

        # Buttons (Centered)
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        button_frame.columnconfigure(0, weight=1)

        ttk.Button(button_frame, text="Go Back", command=self.go_back).grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        ttk.Button(button_frame, text="Refresh", command=self.refresh_file_list).grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        ttk.Button(button_frame, text="Open", command=self.open_file).grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        # Set initial focus to Listbox
        self.file_listbox.focus_set()

    def listbox_keypress(self, event):
        """
        Handle keypress in the Listbox. If alphanumeric key, update the search bar and perform search.
        """
        if event.char.isprintable():  # Check if the key is printable (e.g., letter or number)
            # Enable search entry temporarily to update its value
            self.search_entry.configure(state="normal")
            self.search_var.set(self.search_var.get() + event.char)  # Append the key to search bar
            self.search_entry.configure(state="disabled")  # Disable it back for focus consistency
            self.perform_search()  # Perform search based on updated search query


    def delete_from_search(self, event):
        """
        Handle Backspace in the Listbox to delete characters from the search bar.
        """
        if self.search_var.get():  # Ensure there's something to delete
            # Enable search entry temporarily to update its value
            self.search_entry.configure(state="normal")
            self.search_var.set(self.search_var.get()[:-1])  # Remove the last character
            self.search_entry.configure(state="disabled")  # Disable it back for focus consistency
            self.perform_search()  # Perform search based on updated search query


    def navigate_listbox(self, direction):
        """
        Navigate the Listbox using the arrow keys, moving by one item at a time.
        """
        selected = self.file_listbox.curselection()
        if selected:
            new_index = max(0, min(selected[0] + direction, self.file_listbox.size() - 1))
        else:
            new_index = 0  # If no item is selected, default to the first item

        self.file_listbox.selection_clear(0, tk.END)
        self.file_listbox.selection_set(new_index)
        self.file_listbox.activate(new_index)
        self.file_listbox.see(new_index)  # Ensure the item is visible

        return "break"  # Prevent default Listbox behavior

    def perform_search(self):
        """
        Filter the entries in the Listbox based on the search query.
        """
        query = self.search_var.get().lower()  # Get search input and make it case-insensitive
        filtered_entries = [entry for entry in self.entries if query in entry.lower()]  # Filter entries

        # Update the Listbox with filtered entries
        self.file_listbox.delete(0, tk.END)
        if not filtered_entries:
            self.file_listbox.insert(tk.END, "No matching entries found.")
        else:
            for entry in filtered_entries:
                self.file_listbox.insert(tk.END, entry)

    def refresh_file_list(self):
        """
        Refresh the file list and reset search.
        """
        self.search_var.set("")  # Reset search field
        self.file_listbox.delete(0, tk.END)
        try:
            entries = os.listdir(self.current_path)
            # Separate folders and files, then sort each group
            folders = sorted([entry for entry in entries if os.path.isdir(os.path.join(self.current_path, entry)) and entry != "venv" and not entry.startswith('.')])
            files = sorted([entry for entry in entries if entry.endswith('.csv') and not entry.startswith('.')])

            # Combine sorted folders and files
            self.entries = folders + files

            if not self.entries:
                messagebox.showwarning("No Files", "No folders or CSV files found in the current directory.")
            else:
                for entry in self.entries:
                    self.file_listbox.insert(tk.END, entry)
                # Auto-select the first entry and set focus
                self.file_listbox.selection_set(0)
                self.file_listbox.focus_set()

            # Update current path label with relative path
            relative_path = os.path.relpath(self.current_path, self.program_root)
            self.current_path_label.config(text=f"Current Path: {relative_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load entries:\n{str(e)}")

    def open_selected_file(self):
        """
        Handle double-click to open the selected file or folder.
        """
        selected_index = self.file_listbox.curselection()
        if selected_index:
            self.open_file()  # Reuse the open_file method for consistent behavior

    def open_file(self):
        """
        Open a selected file or folder and reset search.
        """
        selected_index = self.file_listbox.curselection()
        if not selected_index:
            messagebox.showwarning("No Selection", "Please select a file or folder.")
            return

        selected_entry = self.entries[selected_index[0]]
        selected_path = os.path.join(self.current_path, selected_entry)

        self.search_var.set("")  # Reset search field on navigation

        if os.path.isdir(selected_path):
            # Navigate into the folder
            self.current_path = selected_path
            self.refresh_file_list()
        elif selected_path.endswith('.csv'):
            # Load and display the CSV file
            room_name, evidence_entries = load_data(selected_path)
            if evidence_entries:
                self.qr_code_viewer(room_name, evidence_entries)
        else:
            messagebox.showerror("Invalid Selection", "Please select a valid folder or CSV file.")

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
        """
        Display the current QR code, owner, and name.
        """
        inventarizacni_cislo, owner, name = self.evidence_entries[self.index]

        # Remove accents from Inventarizační číslo
        normalized_code = remove_accents(inventarizacni_cislo)
        
        # Update labels with normalized data
        self.label_code.config(text=f"{normalized_code}")
        self.label_owner.config(text=f"{owner}")
        self.label_name.config(text=f"{name}")

        # Generate QR code with normalized data
        qr_image = generate_qr_image(normalized_code).resize((300, 300))
        self.qr_image_tk = ImageTk.PhotoImage(qr_image)
        self.qr_label.config(image=self.qr_image_tk)

        # Update position label with room name and counter (starting from 0)
        self.position_label.config(
            text=f"{self.room_name} - {self.index}/{len(self.evidence_entries) - 1}"
        )

    def show_next(self):
        if self.index < len(self.evidence_entries) - 1:
            self.index += 1
            self.show_qr_code()

    def show_previous(self):
        if self.index > 0:
            self.index -= 1
            self.show_qr_code()
    
    def go_back(self):
        """
        Go back to the parent directory and reset search.
        """
        if hasattr(self, "program_root") and self.current_path != self.program_root:
            self.current_path = os.path.dirname(self.current_path)
            self.search_var.set("")  # Reset search field on navigation
            self.refresh_file_list()

# Run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = InventoryApp(root)
    app.program_root = os.getcwd()  # Set the root directory here
    root.mainloop()