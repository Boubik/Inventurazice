from __future__ import annotations

import csv
import os
import re
import unicodedata
from pathlib import Path

import qrcode
import tkinter as tk
from PIL import Image, ImageTk
from tkinter import messagebox, ttk
from tkinter import font as tkfont

APP_TITLE = "Inventarizace – QR"
BACKGROUND = "#252525"
PANEL = "#303030"
FOREGROUND = "#f5f5f5"
MUTED = "#bdbdbd"
GENERIC_PARENT_DIRS = {"rooms", "room", "out", "inv", "inventory", "inventarizace"}


def clean(value: str | None) -> str:
    return (value or "").replace("\ufeff", "").strip()


def normalize_room(value: str) -> str:
    parts = [part.strip() for part in clean(value).replace("\\", "/").split("/") if part.strip()]
    return "/".join(parts)


def remove_accents(input_str: str) -> str:
    nfkd_form = unicodedata.normalize("NFKD", input_str)
    return "".join(char for char in nfkd_form if not unicodedata.combining(char))


def infer_room_from_path(room: str, csv_file: str | os.PathLike[str]) -> str:
    room = normalize_room(room)
    if not room or "/" in room:
        return room

    path = Path(csv_file)
    parent = clean(path.parent.name)
    parser_output_path = any(ancestor.name.casefold() in {"rooms", "names"} for ancestor in path.parents)
    if (
        parser_output_path
        and parent
        and parent.casefold() not in GENERIC_PARENT_DIRS
        and parent != room
        and re.fullmatch(r"[A-Za-z0-9._-]+", parent)
    ):
        return f"{parent}/{room}"

    stem = path.stem
    prefix = "evidencni_cisla_"
    if stem.casefold().startswith(prefix):
        suffix = stem[len(prefix):]
        room_suffix = "_" + room.replace("/", "_")
        if suffix.endswith(room_suffix):
            building = suffix[: -len(room_suffix)].strip("_")
            if building:
                return normalize_room(f"{building}/{room}")

    return room


def read_csv_rows(csv_file: str | os.PathLike[str]) -> list[list[str]]:
    with open(csv_file, newline="", encoding="utf-8-sig") as csvfile:
        sample = csvfile.read(4096)
        csvfile.seek(0)
        delimiter = ";"
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=";,\t,").delimiter
        except csv.Error:
            pass
        return list(csv.reader(csvfile, delimiter=delimiter))


def looks_like_item_header(row: list[str]) -> bool:
    if not row:
        return False
    first = remove_accents(clean(row[0])).casefold()
    return first.startswith(("inventarizacni cislo", "inventarni cislo", "evidencni cislo"))


def load_data(csv_file: str | os.PathLike[str]) -> tuple[str, list[tuple[str, str, str]]]:
    evidence_entries: list[tuple[str, str, str]] = []
    try:
        rows = read_csv_rows(csv_file)
        first_index = next(
            (index for index, row in enumerate(rows) if row and any(clean(value) for value in row)),
            None,
        )
        if first_index is None:
            return "", []

        first_row = rows[first_index]
        room_name = normalize_room(first_row[0] if first_row else "")
        if len(first_row) > 1:
            description = clean(first_row[1])
            if ":" in description and remove_accents(description).casefold().startswith("mistnost:"):
                described_room = normalize_room(description.split(":", 1)[1])
                if described_room and (not room_name or ("/" in described_room and "/" not in room_name)):
                    room_name = described_room

        room_name = infer_room_from_path(room_name, csv_file)
        if room_name:
            evidence_entries.append((room_name, "", f"Místnost: {room_name}"))

        seen: set[str] = set()
        for row in rows[first_index + 1:]:
            if not row or all(not clean(value) for value in row) or looks_like_item_header(row):
                continue
            inventory_id = clean(row[0]) if row else ""
            if not inventory_id:
                continue
            key = inventory_id.casefold()
            if key in seen:
                continue
            seen.add(key)
            owner = clean(row[1]) if len(row) > 1 else ""
            name = clean(row[2]) if len(row) > 2 else ""
            evidence_entries.append((inventory_id, owner, name))

        return room_name, evidence_entries
    except Exception as exc:
        messagebox.showerror("Chyba", f"Soubor se nepodařilo načíst:\n{csv_file}\n\n{exc}")
        return "", []


def generate_qr_image(content: str) -> Image.Image:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(content)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


class InventoryApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("900x720")
        self.root.minsize(420, 380)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.program_root = Path.cwd().resolve()
        self.current_path = self.program_root
        self.entries: list[str] = []
        self.displayed_entries: list[str] = []
        self.topmost_var = tk.BooleanVar(value=False)
        self.search_var = tk.StringVar(value="")
        self._search_trace = None

        self._resize_after_id: str | None = None
        self._qr_source_image: Image.Image | None = None
        self._qr_photo: ImageTk.PhotoImage | None = None
        self._last_qr_size = 0

        self._room_qr_overlay: tk.Frame | None = None
        self._room_qr_overlay_photo: ImageTk.PhotoImage | None = None

        self._configure_styles()
        self.file_selection_view()

    def _configure_styles(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        self.root.configure(background=BACKGROUND)
        style.configure("TFrame", background=BACKGROUND)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BACKGROUND, foreground=FOREGROUND)
        style.configure("Muted.TLabel", background=BACKGROUND, foreground=MUTED)
        style.configure(
            "Title.TLabel",
            background=BACKGROUND,
            foreground=FOREGROUND,
            font=("TkDefaultFont", 17, "bold"),
        )
        style.configure(
            "Code.TLabel",
            background=BACKGROUND,
            foreground=FOREGROUND,
            font=("TkDefaultFont", 16, "bold"),
        )
        style.configure("TButton", padding=(10, 7))
        style.configure("RoomQr.TButton", padding=(8, 4))
        style.configure("TCheckbutton", background=BACKGROUND, foreground=FOREGROUND)
        style.map("TCheckbutton", background=[("active", BACKGROUND)])

        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(size=max(default_font.cget("size"), 10))

    def _clear_shortcuts(self) -> None:
        for sequence in (
            "<Left>",
            "<Right>",
            "<Escape>",
            "<BackSpace>",
            "<Return>",
            "<KeyPress-i>",
            "<KeyPress-I>",
        ):
            self.root.unbind(sequence)

    def clear_view(self) -> None:
        self._close_room_qr_overlay(restore_shortcuts=False, refocus=False)
        self._clear_shortcuts()

        if self._resize_after_id is not None:
            try:
                self.root.after_cancel(self._resize_after_id)
            except tk.TclError:
                pass
            self._resize_after_id = None

        if self._search_trace is not None:
            try:
                self.search_var.trace_remove("write", self._search_trace)
            except tk.TclError:
                pass
            self._search_trace = None

        self._qr_photo = None

        for widget in self.root.winfo_children():
            widget.destroy()

    def _toggle_topmost(self) -> None:
        self.root.attributes("-topmost", bool(self.topmost_var.get()))

    def _add_header(
        self,
        parent: ttk.Frame,
        title: str,
        subtitle: str = "",
        room_qr_command=None,
    ) -> ttk.Frame:
        header = ttk.Frame(parent)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text=title, style="Title.TLabel").grid(row=0, column=0, sticky="w")

        if subtitle:
            ttk.Label(header, text=subtitle, style="Muted.TLabel").grid(
                row=1, column=0, sticky="w", pady=(2, 0)
            )

        header_rows = 2
        if room_qr_command is not None and subtitle:
            ttk.Button(
                header,
                text="⌖  QR místnosti",
                command=room_qr_command,
                style="RoomQr.TButton",
                takefocus=False,
            ).grid(row=2, column=0, sticky="w", pady=(6, 0))
            header_rows = 3

        ttk.Checkbutton(
            header,
            text="Vždy navrchu",
            variable=self.topmost_var,
            command=self._toggle_topmost,
        ).grid(row=0, column=1, rowspan=header_rows, sticky="ne", padx=(12, 0))

        return header

    def file_selection_view(self) -> None:
        self.clear_view()

        main_frame = ttk.Frame(self.root, padding=16)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)

        relative = os.path.relpath(self.current_path, self.program_root)
        shown_path = "kořen" if relative == "." else relative
        self._add_header(main_frame, "Výběr místnosti / CSV", f"Umístění: {shown_path}")

        search_frame = ttk.Frame(main_frame)
        search_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        search_frame.columnconfigure(1, weight=1)
        ttk.Label(search_frame, text="Hledat:").grid(row=0, column=0, padx=(0, 8))
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=1, sticky="ew")
        ttk.Button(search_frame, text="Vymazat", command=lambda: self.search_var.set("")).grid(
            row=0, column=2, padx=(8, 0)
        )

        self.status_label = ttk.Label(main_frame, text="", style="Muted.TLabel")
        self.status_label.grid(row=2, column=0, sticky="w", pady=(0, 5))

        listbox_frame = ttk.Frame(main_frame)
        listbox_frame.grid(row=3, column=0, sticky="nsew")
        listbox_frame.columnconfigure(0, weight=1)
        listbox_frame.rowconfigure(0, weight=1)

        self.file_listbox = tk.Listbox(
            listbox_frame,
            font=tkfont.nametofont("TkDefaultFont"),
            activestyle="none",
            bg=PANEL,
            fg=FOREGROUND,
            selectbackground="#4b6985",
            selectforeground="#ffffff",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#444444",
            exportselection=False,
        )
        self.file_listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.file_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.file_listbox.configure(yscrollcommand=scrollbar.set)

        self.file_listbox.bind("<Return>", lambda _event: self.open_file())
        self.file_listbox.bind("<Double-1>", lambda _event: self.open_file())
        self.file_listbox.bind("<Key>", self._listbox_type_to_search)
        self.file_listbox.bind("<BackSpace>", self._listbox_backspace)

        buttons = ttk.Frame(main_frame)
        buttons.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        for column in range(3):
            buttons.columnconfigure(column, weight=1)

        ttk.Button(buttons, text="← O úroveň výš", command=self.go_back).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )
        ttk.Button(buttons, text="Obnovit", command=self.refresh_file_list).grid(
            row=0, column=1, sticky="ew", padx=5
        )
        ttk.Button(buttons, text="Otevřít", command=self.open_file).grid(
            row=0, column=2, sticky="ew", padx=(5, 0)
        )

        self._search_trace = self.search_var.trace_add("write", lambda *_args: self.perform_search())
        self.root.bind("<Escape>", lambda _event: self.go_back())

        self.refresh_file_list(reset_search=True)
        self.file_listbox.focus_set()

    def _listbox_type_to_search(self, event: tk.Event) -> str | None:
        if event.keysym in {
            "Up",
            "Down",
            "Left",
            "Right",
            "Return",
            "Escape",
            "BackSpace",
            "Delete",
            "Home",
            "End",
            "Prior",
            "Next",
        }:
            return None

        if event.char and event.char.isprintable():
            self.search_var.set(self.search_var.get() + event.char)
            return "break"
        return None

    def _listbox_backspace(self, _event: tk.Event) -> str:
        if self.search_var.get():
            self.search_var.set(self.search_var.get()[:-1])
        else:
            self.go_back()
        return "break"

    def perform_search(self) -> None:
        if not hasattr(self, "file_listbox") or not self.file_listbox.winfo_exists():
            return

        query = self.search_var.get().strip().casefold()
        self.displayed_entries = [entry for entry in self.entries if query in entry.casefold()]

        self.file_listbox.delete(0, tk.END)
        for entry in self.displayed_entries:
            full_path = self.current_path / entry
            prefix = "📁 " if full_path.is_dir() else "📄 "
            self.file_listbox.insert(tk.END, prefix + entry)

        if self.displayed_entries:
            self.file_listbox.selection_set(0)
            self.file_listbox.activate(0)

        self.status_label.configure(text=f"Zobrazeno: {len(self.displayed_entries)} / {len(self.entries)}")

    def refresh_file_list(self, reset_search: bool = False) -> None:
        if reset_search:
            self.search_var.set("")

        try:
            entries = list(self.current_path.iterdir())
            folders = sorted(
                [
                    entry.name
                    for entry in entries
                    if entry.is_dir() and entry.name != "venv" and not entry.name.startswith(".")
                ],
                key=str.casefold,
            )
            files = sorted(
                [
                    entry.name
                    for entry in entries
                    if entry.is_file()
                    and entry.suffix.casefold() == ".csv"
                    and not entry.name.startswith(".")
                ],
                key=str.casefold,
            )
            self.entries = folders + files
            self.perform_search()
        except OSError as exc:
            messagebox.showerror("Chyba", f"Obsah složky se nepodařilo načíst:\n{exc}")

    def open_file(self) -> None:
        selected = self.file_listbox.curselection()
        if not selected or not self.displayed_entries:
            return

        index = selected[0]
        if index >= len(self.displayed_entries):
            return

        selected_entry = self.displayed_entries[index]
        selected_path = self.current_path / selected_entry

        if selected_path.is_dir():
            self.current_path = selected_path.resolve()
            self.search_var.set("")
            self.file_selection_view()
            return

        if selected_path.suffix.casefold() != ".csv":
            return

        room_name, evidence_entries = load_data(selected_path)
        if evidence_entries:
            self.qr_code_viewer(room_name, evidence_entries)
        else:
            messagebox.showwarning("Prázdný soubor", "V CSV nebyly nalezeny žádné použitelné položky.")

    def qr_code_viewer(self, room_name: str, evidence_entries: list[tuple[str, str, str]]) -> None:
        self.clear_view()
        self.room_name = room_name
        self.evidence_entries = evidence_entries
        self.index = 0

        main_frame = ttk.Frame(self.root, padding=16)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1, minsize=1)

        self._add_header(
            main_frame,
            "QR inventarizace",
            room_name or "Neznámá místnost",
            room_qr_command=self.toggle_room_qr if room_name else None,
        )

        self.position_label = ttk.Label(main_frame, text="", style="Muted.TLabel", anchor="center")
        self.position_label.grid(row=1, column=0, sticky="ew", pady=(0, 5))

        self.label_code = ttk.Label(main_frame, text="", style="Code.TLabel", anchor="center")
        self.label_code.grid(row=2, column=0, sticky="ew", pady=(0, 6))

        self.qr_canvas = tk.Canvas(
            main_frame,
            bg=BACKGROUND,
            highlightthickness=0,
            borderwidth=0,
            relief="flat",
        )
        self.qr_canvas.grid(row=3, column=0, sticky="nsew")

        details = ttk.Frame(main_frame)
        details.grid(row=4, column=0, sticky="ew", pady=(6, 0))
        details.columnconfigure(0, weight=1)

        self.label_owner = ttk.Label(details, text="", anchor="center", justify="center")
        self.label_owner.grid(row=0, column=0, sticky="ew")

        self.label_name = ttk.Label(
            details,
            text="",
            anchor="center",
            justify="center",
            style="Muted.TLabel",
        )
        self.label_name.grid(row=1, column=0, sticky="ew", pady=(3, 0))

        buttons = ttk.Frame(main_frame)
        buttons.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        for column in range(3):
            buttons.columnconfigure(column, weight=1)

        ttk.Button(buttons, text="← Předchozí", command=self.show_previous).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )
        ttk.Button(buttons, text="Menu", command=self.file_selection_view).grid(
            row=0, column=1, sticky="ew", padx=5
        )
        ttk.Button(buttons, text="Další →", command=self.show_next).grid(
            row=0, column=2, sticky="ew", padx=(5, 0)
        )

        self._bind_qr_viewer_shortcuts()

        main_frame.bind("<Configure>", self._update_detail_wrap)
        self.qr_canvas.bind("<Configure>", self._schedule_qr_resize)

        self.show_qr_code()

    def _bind_qr_viewer_shortcuts(self) -> None:
        self.root.bind("<Right>", lambda _event: self.show_next())
        self.root.bind("<Left>", lambda _event: self.show_previous())
        self.root.bind("<Escape>", lambda _event: self.file_selection_view())
        self.root.bind("<BackSpace>", lambda _event: self.file_selection_view())
        self.root.bind("<KeyPress-i>", lambda _event: self.toggle_room_qr())
        self.root.bind("<KeyPress-I>", lambda _event: self.toggle_room_qr())

    def toggle_room_qr(self) -> str:
        if self._room_qr_overlay is not None:
            try:
                if self._room_qr_overlay.winfo_exists():
                    return self._close_room_qr_overlay()
            except tk.TclError:
                self._room_qr_overlay = None

        self._open_room_qr_overlay()
        return "break"

    def _open_room_qr_overlay(self) -> None:
        if not getattr(self, "room_name", ""):
            return

        self.root.update_idletasks()

        for sequence in ("<Left>", "<Right>"):
            self.root.unbind(sequence)
        self.root.bind("<Escape>", lambda _event: self._close_room_qr_overlay())
        self.root.bind("<BackSpace>", lambda _event: self._close_room_qr_overlay())
        self.root.bind("<KeyPress-i>", lambda _event: self._close_room_qr_overlay())
        self.root.bind("<KeyPress-I>", lambda _event: self._close_room_qr_overlay())

        overlay = tk.Frame(self.root, bg=BACKGROUND, highlightthickness=0, borderwidth=0)
        self._room_qr_overlay = overlay
        overlay.place(x=0, y=0, relwidth=1, relheight=1)
        overlay.lift()
        overlay.columnconfigure(0, weight=1)
        overlay.rowconfigure(0, weight=1)

        content = ttk.Frame(overlay, padding=24)
        content.grid(row=0, column=0)
        content.columnconfigure(0, weight=1)

        ttk.Label(content, text="QR místnosti", style="Title.TLabel", anchor="center").grid(
            row=0, column=0, sticky="ew", pady=(0, 4)
        )
        ttk.Label(content, text=self.room_name, style="Code.TLabel", anchor="center").grid(
            row=1, column=0, sticky="ew", pady=(0, 14)
        )

        max_size = min(self.root.winfo_width() - 80, self.root.winfo_height() - 220, 440)
        qr_size = max(180, max_size)
        room_code = remove_accents(self.room_name)
        qr_image = generate_qr_image(room_code)
        resampling = getattr(Image, "Resampling", Image).NEAREST
        qr_image = qr_image.resize((qr_size, qr_size), resampling)
        self._room_qr_overlay_photo = ImageTk.PhotoImage(qr_image)

        ttk.Label(content, image=self._room_qr_overlay_photo).grid(
            row=2, column=0, pady=(0, 14)
        )

        total_items = max(0, len(self.evidence_entries) - 1)
        ttk.Label(
            content,
            text=f"Inventarizace zůstává na pozici {self.index}/{total_items}",
            style="Muted.TLabel",
            anchor="center",
        ).grid(row=3, column=0, sticky="ew", pady=(0, 10))

        ttk.Button(content, text="Zavřít", command=self._close_room_qr_overlay).grid(
            row=4, column=0, sticky="ew"
        )

        overlay.focus_set()

    def _close_room_qr_overlay(
        self,
        restore_shortcuts: bool = True,
        refocus: bool = True,
    ) -> str:
        overlay = self._room_qr_overlay
        self._room_qr_overlay = None
        self._room_qr_overlay_photo = None

        if overlay is not None:
            try:
                if overlay.winfo_exists():
                    overlay.destroy()
            except tk.TclError:
                pass

        if restore_shortcuts and hasattr(self, "evidence_entries") and hasattr(self, "index"):
            self._bind_qr_viewer_shortcuts()

        if refocus:
            try:
                self.root.focus_force()
            except tk.TclError:
                pass

        return "break"

    def _update_detail_wrap(self, event: tk.Event) -> None:
        wrap = max(160, event.width - 40)
        self.label_owner.configure(wraplength=wrap)
        self.label_name.configure(wraplength=wrap)

    def _schedule_qr_resize(self, _event: tk.Event | None = None) -> None:
        if self._resize_after_id is not None:
            try:
                self.root.after_cancel(self._resize_after_id)
            except tk.TclError:
                pass
        self._resize_after_id = self.root.after(25, self._render_qr_for_current_size)

    def _render_qr_for_current_size(self) -> None:
        self._resize_after_id = None

        if self._qr_source_image is None:
            return
        if not hasattr(self, "qr_canvas") or not self.qr_canvas.winfo_exists():
            return

        width = self.qr_canvas.winfo_width()
        height = self.qr_canvas.winfo_height()
        if width <= 2 or height <= 2:
            self._schedule_qr_resize()
            return

        padding = 16
        size = min(width - padding * 2, height - padding * 2)
        if size < 1:
            return

        if size != self._last_qr_size:
            self._last_qr_size = size
            resampling = getattr(Image, "Resampling", Image).NEAREST
            image = self._qr_source_image.resize((size, size), resampling)
            self._qr_photo = ImageTk.PhotoImage(image)

        self.qr_canvas.delete("qr")
        if self._qr_photo is not None:
            self.qr_canvas.create_image(
                width // 2,
                height // 2,
                image=self._qr_photo,
                anchor="center",
                tags="qr",
            )

    def show_qr_code(self) -> None:
        inventory_id, owner, name = self.evidence_entries[self.index]
        normalized_code = remove_accents(inventory_id)

        self.label_code.configure(text=normalized_code)
        self.label_owner.configure(text=owner)
        self.label_name.configure(text=name)

        self._qr_source_image = generate_qr_image(normalized_code)
        self._last_qr_size = 0
        self._qr_photo = None
        self._schedule_qr_resize()

        total_items = max(0, len(self.evidence_entries) - 1)
        if self.index == 0 and self.room_name:
            self.position_label.configure(text=f"Místnost • {self.room_name} • {total_items} položek")
        else:
            self.position_label.configure(text=f"{self.room_name} • {self.index}/{total_items}")

    def show_next(self) -> None:
        if self.index < len(self.evidence_entries) - 1:
            self.index += 1
            self.show_qr_code()

    def show_previous(self) -> None:
        if self.index > 0:
            self.index -= 1
            self.show_qr_code()

    def go_back(self) -> None:
        if self.current_path != self.program_root:
            try:
                self.current_path.relative_to(self.program_root)
            except ValueError:
                self.current_path = self.program_root
            else:
                self.current_path = self.current_path.parent

            self.search_var.set("")
            self.file_selection_view()


if __name__ == "__main__":
    root = tk.Tk()
    InventoryApp(root)
    root.mainloop()
