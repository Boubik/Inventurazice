# Inventory QR Code Viewer

Desktop utility for preparing inventory CSV exports and displaying QR codes for rooms and individual assets.

## Components

- `parser.py` – imports one or more CSV files and creates normalized outputs under `out/`.
- `run.py` – scalable Tkinter QR viewer for the generated CSV files.
- `js.txt` – browser snippet for exporting the currently displayed inventory table to CSV.

## Parser

The parser recognizes two distinct input types and **keeps their outputs separate**.

### 1. Room exports

Room exports have three columns and usually come from `js.txt`:

```csv
64/7.06;Místnost: 64/7.06;
1003201/1;Owner;Projector
```

They are written to:

```text
out/
├── rooms/
│   └── 64/
│       └── 7.06.csv
└── names/
    └── Owner Name/
        └── 64/
            └── 7.06.csv
```

Duplicates are removed only within the room-export dataset. If the same room appears once as `7.06` and once as `64/7.06`, the fully qualified form is preferred.

### 2. MANKO export

The official MANKO CSV contains owner sections and a 7-column table. The important fields are:

- column 0 – inventory number
- column 1 – item name
- column 5 – full location such as `64/7.06`
- rows beginning with `Odpovědná osoba:` / `Odpovědná ososba:` identify the owner

MANKO is always generated into its own namespace:

```text
out/
└── manko/
    ├── rooms/
    │   └── 64/
    │       └── 7.06.csv
    └── names/
        └── Owner Name/
            └── 64/
                └── 7.06.csv
```

MANKO records are **not merged or deduplicated with normal room exports**. The same inventory number may therefore exist once in `out/rooms/...` and separately in `out/manko/rooms/...`, which is intentional.

### Usage

Process explicit files:

```bash
python parser.py MANKO.csv evidencni_cisla_64_7.06.csv
```

Process a directory recursively:

```bash
python parser.py ./exports
```

With no input arguments, all CSV files below the current directory are scanned. The selected output directory is excluded automatically:

```bash
python parser.py
```

Choose another output directory:

```bash
python parser.py ./exports --output prepared
```

Each dataset is regenerated only when an input of that type is present. For example, running the parser only with room exports leaves an existing `out/manko/` untouched, and running it only with MANKO leaves the normal `out/rooms/` and `out/names/` untouched.

## QR viewer

Install dependencies:

```bash
pip install -r requirements.txt
```

Run:

```bash
python run.py
```

The application lets you browse folders and CSV files, search, and move through room/item QR codes using the buttons or the left/right arrow keys.

### Window behavior

The window is no longer forced to stay above other applications. Use the `Vždy navrchu` checkbox when you temporarily want always-on-top behavior.

The layout and QR image resize with the window, and the minimum window size is smaller so the application can be used next to another program.

## Browser export (`js.txt`)

The browser helper tries to export the full room ID, for example `64/7.06`, instead of only `7.06`. It first looks for a full location already rendered on the page and then falls back to common building/object form controls.

If the source page does not expose the building anywhere, JavaScript cannot infer it reliably. In that case it keeps the room value it can see and logs a warning in the browser console.

The CSV writer also quotes values containing semicolons, quotes, or line breaks.

## Tests

Parser regression tests use only the Python standard library:

```bash
python -m unittest discover -s tests -v
```

## Requirements

- Python 3.8+
- tkinter (normally bundled with Python)
- qrcode
- Pillow

## License

MIT – see `LICENSE`.
