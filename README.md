# PDF Language Translator

This Python script translates PDF documents from a source language to a target language, generating an HTML file as output. It is optimized for multi-core CPUs by processing PDF pages in parallel.

## Features

- Translates text between any two languages supported by Google Translate or using a local MarianMT model.
- Extracts images from the PDF and embeds them in the output HTML.
- Automatic detection and conversion of both internal (table of contents) and external (web) hyperlinks.
- Preserves the original top-to-bottom order of text and images.
- Uses multithreading to accelerate the translation of multi-page documents.
- Command-line interface for ease of use.

## Requirements

- Python 3.x
- The dependencies listed in `requirements.txt` (and potentially `sentencepiece` and `sacremoses` for local models)

## Installation

1. Clone the repository or download the source code.
2. Navigate to the project directory.
3. It is highly recommended to use a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
4. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the script from your terminal using the following command structure:

```bash
python3 translate_pdf.py <input_pdf> <output_html> [-s <source_lang>] [-t <target_lang>] [--translator <google|local>]
```

### Arguments

- `<input_pdf>`: (Required) The path to the source PDF file.
- `<output_html>`: (Required) The path for the generated HTML output file.
- `-s, --source`: (Optional) The source language code. Defaults to `'en'` (English).
- `-t, --target`: (Optional) The target language code. Defaults to `'it'` (Italian).
- `--translator`: (Optional) Specifies the translation service to use. Options are `google` (for Google Translate API) or `local` (for a local Hugging Face MarianMT model). Defaults to `google`.

### Examples

- **Default (English to Italian, using Google Translator):**
  ```bash
  python3 translate_pdf.py my_document.pdf translated_document.html
  ```

- **Spanish to French (using Google Translator):**
  ```bash
  python3 translate_pdf.py report.pdf report_fr.html --source es --target fr
  ```

- **English to Italian (using local model):**
  ```bash
  python3 translate_pdf.py my_document.pdf translated_document.html --translator local
  ```

- **French to Italian (using local model):**
  ```bash
  python3 translate_pdf.py st_exupery_le_petit_prince.pdf le_petit_prince_it.html --source fr --target it --translator local
  ```

### Example with Included File

This repository includes the French text of "Le Petit Prince" (`st_exupery_le_petit_prince.pdf`), which is in the public domain in most countries. You can use it to test the translation from French to Italian:

```bash
python3 translate_pdf.py st_exupery_le_petit_prince.pdf le_petit_prince_it.html --source fr --target it --translator local
```
