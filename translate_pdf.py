import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import concurrent.futures
import argparse
import os
import sys
import base64
import re
from collections import Counter

# Import from our new module
from local_translation import initialize_model, translate_local

def translate_google(text, source_lang, target_lang):
    """Wrapper for Google Translator to have a consistent function signature."""
    if not text.strip():
        return ""
    try:
        return GoogleTranslator(source=source_lang, target=target_lang).translate(text)
    except Exception as e:
        print(f"Errore durante la traduzione con GoogleTranslator: {e}", file=sys.stderr)
        return f"Errore di traduzione (Google): {text}"

def translate_page_content(page_num, pdf_path, translate_func, source_lang, target_lang):
    """
    Handles text, links (internal & external), and images for a single PDF page.
    This version identifies link text, protects it from translation, and recreates
    the appropriate HTML links (<a>) in the final output, and attempts to preserve
    basic text styling (size, bold, italic) for paragraphs.
    """
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_num)

        # 1. Extract all content types: links, images, and text spans
        links = page.get_links()
        image_list = page.get_images(full=True)
        blocks = page.get_text("dict").get("blocks", [])

        # 2. Create a unified list of all content items with their bounding boxes
        page_items = []
        for block in blocks:
            if block["type"] == 0: # Text block
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        if (span['bbox'][3] - span['bbox'][1]) > 5:
                            # Store size and flags for styling
                            page_items.append({"type": "text", "bbox": span["bbox"], "text": span["text"], "size": span["size"], "flags": span["flags"]})
        
        for img_info in image_list:
            try:
                page_items.append({"type": "image", "bbox": page.get_image_bbox(img_info), "xref": img_info[0]})
            except ValueError:
                pass # Skip images that can't be placed

        # Add link information to text items
        for item in page_items:
            if item["type"] == "text":
                for link in links:
                    if fitz.Rect(item["bbox"]).intersects(link["from"]):
                        item["type"] = "link"
                        if link["kind"] == fitz.LINK_URI:
                            item["dest"] = link["uri"]
                        elif link["kind"] == fitz.LINK_GOTO:
                            item["dest"] = link["page"]
                        break

        page_items.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))

        if not page_items:
            doc.close()
            return ""

        # 3. Group items into paragraphs
        grouped_content = []
        current_paragraph = []
        for i, item in enumerate(page_items):
            if item["type"] == "image":
                if current_paragraph:
                    grouped_content.append({"type": "paragraph", "items": current_paragraph})
                    current_paragraph = []
                grouped_content.append(item)
                continue

            if not current_paragraph:
                current_paragraph.append(item)
            else:
                prev_item = current_paragraph[-1]
                vertical_gap = item["bbox"][1] - prev_item["bbox"][3]
                line_height = prev_item["bbox"][3] - prev_item["bbox"][1]
                
                # Check for indentation
                indentation_threshold = 15 # pixels
                is_indented = (item["bbox"][0] - prev_item["bbox"][0]) > indentation_threshold

                if vertical_gap < line_height * 0.1 and not is_indented: # Combine if very small gap AND no significant indentation
                    current_paragraph.append(item)
                else: # Start new paragraph if larger gap OR significant indentation
                    grouped_content.append({"type": "paragraph", "items": current_paragraph})
                    current_paragraph = [item]
        
        if current_paragraph:
            grouped_content.append({"type": "paragraph", "items": current_paragraph})

        # 4. Translate and generate HTML
        final_html_parts = []
        for group in grouped_content:
            if group["type"] == "image":
                try:
                    img = doc.extract_image(group["xref"])
                    b64_img = base64.b64encode(img["image"]).decode('utf-8')
                    final_html_parts.append(f'<div style="text-align: center; margin: 20px 0;"><img src="data:image/{img["ext"]};base64,{b64_img}" style="max-width: 90%; height: auto; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"></div>')
                except Exception as e:
                    print(f"Warning: Could not extract image {group['xref']} on page {page_num + 1}. Error: {e}", file=sys.stderr)
            
            elif group["type"] == "paragraph":
                text_to_translate = ""
                
                # Determine dominant style for the paragraph
                sizes = [item['size'] for item in group['items'] if item['type'] == 'text']
                flags = [item['flags'] for item in group['items'] if item['type'] == 'text']

                dominant_size = Counter(sizes).most_common(1)[0][0] if sizes else 12 # Default size if no text
                dominant_flags = Counter(flags).most_common(1)[0][0] if flags else 0 # Default flags

                style_str = f"font-size: {round(dominant_size)}px;"
                if dominant_flags & 2**4: # Check for bold flag (FLAG_BOLD)
                    style_str += " font-weight: bold;"
                if dominant_flags & 2**1: # Check for italic flag (FLAG_ITALIC)
                    style_str += " font-style: italic;"

                for item in group["items"]:
                    if item["type"] == "link":
                        text_to_translate += f' <span class="notranslate">{item["text"]}</span> '
                    else:
                        text_to_translate += item["text"]
                
                try:
                    # Simplified, consistent translation call
                    translated_text = translate_func(text_to_translate, source_lang, target_lang)
                    
                    if not translated_text: continue

                    # Re-insert links
                    link_items = [item for item in group["items"] if item["type"] == "link"]
                    for i, item in enumerate(link_items):
                        url = item["dest"]
                        link_text = item["text"]
                        if isinstance(url, int): # Internal link
                            href = f"#page-{url}"
                        else: # External link
                            href = url if url.startswith('http') else f"http://{url}"
                        
                        link_tag = f'<a href="{href}">{link_text}</a>'
                        translated_text = re.sub(f'<span class="notranslate">\s*{re.escape(link_text)}\s*</span>', link_tag, translated_text, 1)

                    final_html_parts.append(f"<p style='{style_str}'>{translated_text}</p>")

                except Exception as e:
                    print(f"Warning: Could not translate paragraph on page {page_num + 1}. Error: {e}", file=sys.stderr)
                    final_html_parts.append(f'<p style="color:red;"><strong>[Translation Failed]</strong></p>')

        # Add a page anchor and footer
        page_anchor = f'<div id="page-{page_num}"></div>'
        page_footer = f'<div><hr><p style="text-align:center; color: #888;">--- Page {page_num + 1} ---</p></div>'
        final_html_parts.insert(0, page_anchor)
        final_html_parts.append(page_footer)

        doc.close()
        return "\n".join(final_html_parts)

    except Exception as e:
        error_message = f"Error processing page {page_num + 1}: {e}"
        print(error_message, file=sys.stderr)
        return f'<p style="color:red;"><strong>{error_message}</strong></p>'

def main():
    parser = argparse.ArgumentParser(
        description="Translate a PDF from a source language to a target language, including images and links.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("input_pdf", help="Path to the input PDF file.")
    parser.add_argument("output_html", help="Path for the output HTML file.")
    parser.add_argument("-s", "--source", default='en', help="Source language code. Default: 'en'.")
    parser.add_argument("-t", "--target", default='it', help="Target language code. Default: 'it'.")
    parser.add_argument("--translator", default='google', choices=['google', 'local'], help="Translator to use. 'google' for Google Translate API, 'local' for local Hugging Face model. Default: 'google'.")
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

    # Translator selection
    translate_func = None
    if args.translator == 'local':
        print("Using local Hugging Face model for translation.")
        model_name = f"Helsinki-NLP/opus-mt-{args.source}-{args.target}"
        initialize_model(model_name)
        translate_func = translate_local
    else: # 'google'
        print("Using GoogleTranslator for translation.", file=sys.stderr)
        translate_func = translate_google


    print(f"Source: {args.source}, Target: {args.target}")
    print(f"Starting translation of '{args.input_pdf}' ({num_pages} pages), with full link and paragraph handling...")

    translated_pages = [""] * num_pages

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_page = {executor.submit(translate_page_content, i, pdf_path, translate_func, args.source, args.target): i for i in range(num_pages)}

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
            font-family: Georgia, serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 20px auto;
            padding: 0 20px;
            background-color: #f8f9fa;
            color: #212529;
        }}
        p {{
            text-align: justify;
            margin: 1em 0;
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
        a {{ color: #0056b3; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
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
