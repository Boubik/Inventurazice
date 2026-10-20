# Inventory QR Code Viewer

Desktop utility for preparing inventory CSV exports and displaying QR codes for rooms and individual assets.

## Components

- `parser.py` – imports one or more CSV files and creates normalized room/owner views under `out/`.
- `run.py` – scalable Tkinter QR viewer for the generated CSV files.
- `js.txt` – browser snippet for exporting the currently displayed inventory table to CSV.

## Parser

The parser accepts both formats used by this project:

1. Room exports with three columns:

```csv
64/7.06;Místnost: 64/7.06;
1003201/1;Owner;Projector
```

2. The older 6+ column inventory export where the location is stored in column 6.

### Usage

Process explicit files:

```bash
python parser.py export1.csv export2.csv export3.csv
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

Outputs are regenerated on every run:

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

Inventory numbers are deduplicated across all supplied inputs. Re-running the parser with the same sources does not append duplicate rows. If the same room appears once as `7.06` and once as `64/7.06`, the fully qualified form is preferred. Genuine conflicts are reported in the console and the later input wins.

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
