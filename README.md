# Inventarizace – QR

Nástroj pro převod inventárních dat z IMIS do přehledných CSV souborů podle místností / odpovědných osob a jejich následné zobrazování jako QR kódů.

Celý běžný postup je:

```text
IMIS
  ↓
js_auto.txt / js.txt
  ↓
CSV export
  ↓
parser.py
  ↓
out/
  ↓
run.py
  ↓
QR kódy místností a jednotlivých inventárních položek
```

> [!IMPORTANT]
> Aplikaci i parser je nejlepší spouštět z kořenové složky repozitáře, tedy ze složky, ve které jsou `parser.py`, `run.py` a `requirements.txt`.

## Obsah

- [1. Instalace a závislosti](#1-instalace-a-závislosti)
- [2. Export dat z IMIS](#2-export-dat-z-imis)
  - [Doporučená varianta – `js_auto.txt`](#doporučená-varianta--js_autotxt)
  - [Ruční varianta – `js.txt`](#ruční-varianta--jstxt)
- [3. Kam uložit stažený CSV soubor](#3-kam-uložit-stažený-csv-soubor)
- [4. Spuštění parseru](#4-spuštění-parseru)
- [5. Co vznikne ve složce `out`](#5-co-vznikne-ve-složce-out)
- [6. Spuštění QR aplikace](#6-spuštění-qr-aplikace)
- [7. Ovládání aplikace a klávesové zkratky](#7-ovládání-aplikace-a-klávesové-zkratky)
- [8. Kompletní příklad od exportu po QR](#8-kompletní-příklad-od-exportu-po-qr)
- [9. MANKO export](#9-manko-export)
- [10. Řešení častých problémů](#10-řešení-častých-problémů)

---

## 1. Instalace a závislosti

### Požadavky

- Python **3.8+**
- `tkinter`
- `qrcode`
- `Pillow`

Python balíčky `qrcode` a `Pillow` jsou uvedené v `requirements.txt`.

### Stažení projektu

```bash
git clone https://github.com/Boubik/Inventurazice.git
cd Inventurazice
```

### Doporučeně: virtuální prostředí

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
```

Pokud virtuální prostředí používat nechcete, stačí:

```bash
python -m pip install -r requirements.txt
```

---

## 2. Export dat z IMIS

V repozitáři jsou dva JavaScriptové exportní skripty:

| Soubor | Použití |
|---|---|
| `js_auto.txt` | **Doporučená varianta.** Automaticky projde místnosti daného objektu a vytvoří jeden souhrnný CSV export. |
| `js.txt` | Ruční varianta. Exportuje data z právě zobrazené tabulky / místnosti v IMIS. |

### Doporučená varianta – `js_auto.txt`

`js_auto.txt` automaticky prochází místnosti objektu, načítá inventární položky a na konci stáhne jeden CSV soubor.

Aktuálně je skript nastaven pro objekt:

```javascript
buildingPrefix: '64/'
```

Výchozí název exportu je:

```text
evidencni_cisla_auto_64.csv
```

Pokud chcete exportovat jiný objekt, změňte v `js_auto.txt` minimálně:

```javascript
buildingPrefix: '64/',
outputFileName: 'evidencni_cisla_auto_64.csv',
```

na odpovídající hodnoty.

### Jak `js_auto.txt` spustit

1. Přihlaste se do **IMIS**.
2. Otevřete stránku s inventářem, kde je dostupný filtr místnosti a tabulka inventárních položek.
3. Otevřete vývojářské nástroje prohlížeče:
   - Windows / Linux: `F12` nebo `Ctrl + Shift + I`
   - macOS: `⌥ Option + ⌘ Command + I`
4. Přepněte se na záložku **Console / Konzole**.
5. Otevřete soubor `js_auto.txt` z tohoto repozitáře a zkopírujte **celý jeho obsah**.
6. Vložte skript do konzole a potvrďte klávesou `Enter`.
7. V pravém dolním rohu stránky se objeví panel **Automatický export místností**.
8. Nechte export doběhnout. Skript postupně zobrazuje počet požadavků, nalezených místností a položek.
9. Po dokončení prohlížeč automaticky stáhne CSV soubor, například:

```text
evidencni_cisla_auto_64.csv
```

Skript posílá dotazy postupně a mezi požadavky má prodlevu. Pokud IMIS vrátí limit `>9000`, skript příslušnou část automaticky rozdělí na menší dotazy.

> [!NOTE]
> Během automatického exportu nezavírejte záložku s IMIS. Export lze zrušit tlačítkem `Zrušit` v informačním panelu.

### Ruční varianta – `js.txt`

`js.txt` je vhodný, pokud chcete exportovat pouze konkrétní místnost nebo právě zobrazený výsledek.

Postup:

1. V IMIS nastavte požadovanou místnost / filtr.
2. Nechte zobrazit tabulku inventárních položek.
3. Otevřete `F12` → **Console / Konzole**.
4. Zkopírujte celý obsah `js.txt`.
5. Vložte ho do konzole a potvrďte `Enter`.
6. Prohlížeč stáhne CSV soubor s názvem podobným:

```text
evidencni_cisla_64_7.06.csv
```

Skript se pokouší zjistit plné označení místnosti, například `64/7.06`, nikoliv pouze `7.06`.

---

## 3. Kam uložit stažený CSV soubor

Stažené CSV soubory ukládejte do složky `inv/` v kořeni projektu:

```text
Inventurazice/
├── inv/
│   └── evidencni_cisla_auto_64.csv
├── js.txt
├── js_auto.txt
├── parser.py
├── requirements.txt
└── run.py
```

Potom stažený soubor z `Downloads / Stažené` zkopírujte do `inv/`.

Parser při spuštění automaticky prohledá CSV soubory v projektu a jeho podsložkách. Výstupní složku `out/` při hledání vstupních souborů ignoruje.

> [!WARNING]
> Exporty mohou obsahovat inventární údaje a jména odpovědných osob. Repozitář je veřejný, proto exportované CSV soubory **necommitujte na GitHub**.

---

## 4. Spuštění parseru

Parser vezme exportované CSV soubory a vytvoří strukturu použitelnou QR aplikací.

Z kořenové složky projektu spusťte:

```bash
python parser.py
```

Parser automaticky:

- projde aktuální složku a její podsložky,
- najde CSV soubory,
- rozpozná podporované exporty,
- vytvoří výslednou strukturu do `out/`,
- při hledání vstupů ignoruje samotné `out/`.

---

## 5. Co vznikne ve složce `out`

Po úspěšném zpracování běžného exportu vznikne například:

```text
out/
├── rooms/
│   └── 64/
│       ├── 7.06.csv
│       ├── 7.07.csv
│       └── 7.08.csv
└── names/
    ├── Jan Novák/
    │   └── 64/
    │       └── 7.06.csv
    └── Jana Nováková/
        └── 64/
            └── 7.08.csv
```

### `out/rooms/`

Data jsou rozdělena podle místností.

Typická cesta:

```text
out/rooms/64/7.06.csv
```

### `out/names/`

Stejná data jsou rozdělena podle odpovědné osoby a následně místnosti.

Typická cesta:

```text
out/names/Jméno osoby/64/7.06.csv
```

Parser zároveň odstraňuje / slučuje duplicity uvnitř stejného typu exportu a preferuje plné označení místnosti, například `64/7.06` před samotným `7.06`.

---

## 6. Spuštění QR aplikace

Nejdříve se ujistěte, že jste v kořenové složce projektu:

```bash
cd Inventurazice
```

Potom spusťte:

```bash
python run.py
```

Aplikace začne procházení souborů v adresáři, **ze kterého byla spuštěna**. Proto je doporučeno spouštět ji přímo z kořene repozitáře.

Po spuštění typicky otevřete:

```text
out → rooms → 64 → 7.06.csv
```

Případně lze inventář procházet podle odpovědné osoby:

```text
out → names → Jméno osoby → 64 → 7.06.csv
```

Po otevření CSV se zobrazí QR kódy:

1. první QR kód reprezentuje **místnost**,
2. další QR kódy reprezentují jednotlivá **inventární / evidenční čísla**,
3. pod QR kódem se zobrazuje odpovědná osoba a název položky.

Velikost QR kódu se automaticky přizpůsobuje velikosti okna.

Volba **Vždy navrchu** udrží okno aplikace nad ostatními programy.

---

## 7. Ovládání aplikace a klávesové zkratky

### Výběr souboru / místnosti

| Akce | Ovládání |
|---|---|
| Pohyb v seznamu | `↑` / `↓` |
| Otevřít složku nebo CSV | `Enter` |
| Otevřít myší | dvojklik |
| O úroveň výš | `Esc` |
| Hledání | začněte rovnou psát |
| Smazat poslední znak hledání | `Backspace` |
| Vymazat hledání | tlačítko `Vymazat` |
| Znovu načíst obsah složky | tlačítko `Obnovit` |

Při psaní není nutné nejdříve klikat do vyhledávacího pole. Pokud je aktivní seznam, běžné psaní se automaticky používá jako hledání.

### Zobrazení QR kódu

| Akce | Klávesa |
|---|---|
| Další QR kód | `→` |
| Předchozí QR kód | `←` |
| Návrat do výběru souborů | `Esc` |

Stejné akce jsou dostupné také přes tlačítka `Předchozí`, `Menu` a `Další`.

---

## 8. Kompletní příklad od exportu po QR

Příklad pro automatický export objektu `64`:

### 1. V IMIS

Otevřete inventář → `F12` → `Console` → vložte obsah `js_auto.txt` → `Enter`.

Po dokončení se například stáhne:

```text
evidencni_cisla_auto_64.csv
```

### 2. Přesuňte CSV do projektu

```text
Inventurazice/inv/evidencni_cisla_auto_64.csv
```

### 3. Spusťte parser

```bash
cd Inventurazice
python parser.py
```

Výsledkem bude například:

```text
out/rooms/64/7.06.csv
out/rooms/64/7.07.csv
out/rooms/64/7.08.csv
...
```

### 4. Spusťte aplikaci

```bash
python run.py
```

### 5. V aplikaci

Otevřete například:

```text
out → rooms → 64 → 7.06.csv
```

Následně lze klávesami `←` a `→` procházet QR kód místnosti a jednotlivých inventárních položek.

---

## 9. MANKO export

Parser podporuje také oficiální MANKO CSV export.

MANKO používá jinou strukturu než exporty z `js.txt` / `js_auto.txt`, proto se ukládá odděleně:

```text
out/
└── manko/
    ├── rooms/
    │   └── 64/
    │       └── 7.06.csv
    └── names/
        └── Jméno osoby/
            └── 64/
                └── 7.06.csv
```

MANKO CSV stačí stejně jako ostatní exporty vložit do `inv/` a spustit:

```bash
python parser.py
```

MANKO data se **neslučují** s běžnými exporty. Stejné inventární číslo tedy může existovat jednou v `out/rooms/...` a zároveň v `out/manko/rooms/...`.

---

## 10. Řešení častých problémů

### `ModuleNotFoundError: No module named 'qrcode'`

Nainstalujte Python závislosti:

```bash
python -m pip install -r requirements.txt
```

Pokud používáte virtuální prostředí, nejprve ho aktivujte.

### Parser píše `No input CSV files found. Nothing to do.`

Zkontrolujte, že je CSV soubor uložený pod kořenovou složkou projektu, doporučeně v:

```text
inv/
```

Potom parser spusťte z kořene projektu:

```bash
python parser.py
```

### Aplikace nevidí `out/`

Pravděpodobně byla spuštěna z jiné pracovní složky.

Spusťte ji z kořene projektu:

```bash
cd Inventurazice
python run.py
```

### `js_auto.txt` nenajde žádná data

Zkontrolujte zejména:

- že jste skript spustili na správné stránce IMIS,
- že je dostupný filtr místnosti a inventární tabulka,
- že `buildingPrefix` odpovídá objektu, který chcete exportovat,
- chybové zprávy v `Console / Konzoli` prohlížeče.

### Automatický export skončil chybou

`js_auto.txt` zobrazuje stav přímo v pravém dolním rohu stránky a podrobnosti zapisuje také do konzole prohlížeče. Pokud export není kompletní, CSV se záměrně nevytvoří jako hotový výstup.

---

## Soubory projektu

| Soubor | Účel |
|---|---|
| `js_auto.txt` | Automatický export inventáře z IMIS pro celý objekt. |
| `js.txt` | Export aktuálně zobrazené tabulky / místnosti z IMIS. |
| `parser.py` | Zpracování CSV a vytvoření struktury `out/`. |
| `run.py` | Tkinter aplikace pro procházení CSV a zobrazování QR kódů. |
| `requirements.txt` | Python závislosti pro QR aplikaci. |

## Testy

Pokud jsou v pracovní kopii dostupné parser testy, lze je spustit:

```bash
python -m unittest discover -s tests -v
```

## Licence

MIT – viz `LICENSE`.