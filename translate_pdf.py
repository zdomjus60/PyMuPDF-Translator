

import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import concurrent.futures
import argparse
import os
import sys
import base64

def translate_page_content(page_num, pdf_path, source_lang, target_lang):
    """
    Translates text and embeds images for a single PDF page.

    This function is designed to be run in a separate thread. It opens the PDF,
    extracts both text and image elements, sorts them by vertical position,
    translates the text, and formats everything into an HTML snippet.

    Args:
        page_num (int): The page number to process (0-indexed).
        pdf_path (str): The absolute path to the PDF file.
        source_lang (str): The source language code (e.g., 'en').
        target_lang (str): The target language code (e.g., 'it').

    Returns:
        str: An HTML string containing the translated content and images of the page.
    """
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_num)
        
        page_items = []
        translator = GoogleTranslator(source=source_lang, target=target_lang)

        # 1. Extract text blocks
        text_blocks = page.get_text("dict").get("blocks", [])
        for block in text_blocks:
            if block["type"] == 0:  # It's a text block
                block_text = ""
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        block_text += span.get("text", "") + " "
                block_text = block_text.strip()
                if block_text:
                    page_items.append({"type": "text", "bbox": block["bbox"], "content": block_text})

        # 2. Extract image references
        image_list = page.get_images(full=True)
        for img_info in image_list:
            xref = img_info[0]
            try:
                bbox = page.get_image_bbox(img_info)
                page_items.append({"type": "image", "bbox": bbox, "xref": xref})
            except ValueError as e:
                print(f"Info: Skipping image with xref {xref} on page {page_num + 1}. Reason: {e}", file=sys.stderr)

        # 3. Sort all items by their vertical position
        page_items.sort(key=lambda item: item["bbox"][1])

        # 4. Process sorted items and generate HTML
        translated_html_parts = []
        for item in page_items:
            if item["type"] == "text":
                original_text = item["content"]
                original_text = original_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                try:
                    translated_text = translator.translate(original_text)
                    if translated_text:
                        translated_html_parts.append(f"<p>{translated_text}</p>")
                except Exception as e:
                    print(f"Warning: Could not translate a block on page {page_num + 1}. Error: {e}", file=sys.stderr)
                    translated_html_parts.append(f'<p><em>[Translation Failed]</em> {original_text}</p>')
            
            elif item["type"] == "image":
                try:
                    img = doc.extract_image(item["xref"])
                    img_bytes = img["image"]
                    img_ext = img["ext"]
                    b64_img = base64.b64encode(img_bytes).decode('utf-8')
                    translated_html_parts.append(f'<div style="text-align: center; margin: 20px 0;"><img src="data:image/{img_ext};base64,{b64_img}" style="max-width: 90%; height: auto; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"></div>')
                except Exception as e:
                    print(f"Warning: Could not extract image with xref {item['xref']} on page {page_num + 1}. Error: {e}", file=sys.stderr)

        page_footer = f'<div><hr><p style="text-align:center; color: #888;">--- Page {page_num + 1} ---</p></div>'
        translated_html_parts.append(page_footer)

        doc.close()
        return "\n".join(translated_html_parts)

    except Exception as e:
        error_message = f"Error processing page {page_num + 1}: {e}"
        print(error_message, file=sys.stderr)
        return f'<p style="color:red;"><strong>{error_message}</strong></p>'

def main():
    """
    Main function to orchestrate the PDF translation process.
    """
    parser = argparse.ArgumentParser(
        description="Translate a PDF from a source language to a target language, including images.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("input_pdf", help="Path to the input PDF file.")
    parser.add_argument("output_html", help="Path for the output HTML file.")
    parser.add_argument("-s", "--source", default='en', help="Source language code (e.g., 'en' for English). Default is 'en'.")
    parser.add_argument("-t", "--target", default='it', help="Target language code (e.g., 'it' for Italian). Default is 'it'.")
    args = parser.parse_args()

    if not os.path.exists(args.input_pdf):
        print(f"Error: Input file not found at '{args.input_pdf}'", file=sys.stderr)
        sys.exit(1)

    pdf_path = os.path.abspath(args.input_pdf)

    try:
        doc = fitz.open(pdf_path)
        num_pages = len(doc)
        doc.close()
    except Exception as e:
        print(f"Error: Could not open or read PDF file. Reason: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Source: {args.source}, Target: {args.target}")
    print(f"Starting translation of '{args.input_pdf}' ({num_pages} pages), including images...")

    translated_pages = [""] * num_pages

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_page = {executor.submit(translate_page_content, i, pdf_path, args.source, args.target): i for i in range(num_pages)}

        for i, future in enumerate(concurrent.futures.as_completed(future_to_page)):
            page_num = future_to_page[future]
            try:
                translated_pages[page_num] = future.result()
            except Exception as e:
                error_message = f"Critical error processing page {page_num + 1}: {e}"
                print(error_message, file=sys.stderr)
                translated_pages[page_num] = f'<p style="color:red;"><strong>{error_message}</strong></p>'
            
            progress = (i + 1) / num_pages * 100
            print(f"Progress: {progress:.2f}% completed.", end='\r')

    print("\nTranslation finished. Assembling HTML file...")

    body_content = "\n".join(translated_pages)

    final_html = f"""
<!DOCTYPE html>
<html lang="{args.target}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Translation of {os.path.basename(args.input_pdf)}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 20px auto;
            padding: 0 20px;
            background-color: #f8f9fa;
            color: #212529;
        }}
        p {{
            text-align: justify;
            margin: 0 0 1em 0;
        }}
        h1 {{
            color: #343a40;
        }}
        hr {{
            border: 0;
            height: 1px;
            background: #dee2e6;
            margin: 2em 0;
        }}
    </style>
</head>
<body>
    <h1>Translation of {os.path.basename(args.input_pdf)}</h1>
    {body_content}
</body>
</html>
"""

    try:
        with open(args.output_html, "w", encoding="utf-8") as f:
            f.write(final_html)
        print(f"Successfully saved translated HTML to '{args.output_html}'")
    except IOError as e:
        print(f"Error: Could not write to output file '{args.output_html}'. Reason: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
