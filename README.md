# PDF Language Translator

This Python script translates PDF documents from a source language to a target language, generating an HTML file as output. It is optimized for multi-core CPUs by processing PDF pages in parallel.

## Features

- Translates text between any two languages supported by Google Translate.
- Extracts images from the PDF and embeds them in the output HTML.
- Preserves the original top-to-bottom order of text and images.
- Uses multithreading to accelerate the translation of multi-page documents.
- Command-line interface for ease of use.

## Requirements

- Python 3.x
- The dependencies listed in `requirements.txt`

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
python3 translate_pdf.py <input_pdf> <output_html> [-s <source_lang>] [-t <target_lang>]
```

### Arguments

- `<input_pdf>`: (Required) The path to the source PDF file.
- `<output_html>`: (Required) The path for the generated HTML output file.
- `-s, --source`: (Optional) The source language code. Defaults to `'en'` (English).
- `-t, --target`: (Optional) The target language code. Defaults to `'it'` (Italian).

### Examples

- **Default (English to Italian):**
  ```bash
  python3 translate_pdf.py my_document.pdf translated_document.html
  ```

- **Spanish to French:**
  ```bash
  python3 translate_pdf.py report.pdf report_fr.html --source es --target fr
  ```