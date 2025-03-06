# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "beautifulsoup4",
#     "ebooklib",
#     "pillow",
#     "requests",
# ]
# ///
import os
import re
import json
import html
import mimetypes
import requests
from PIL import Image
from io import BytesIO
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from ebooklib import epub

BASE_URL = "https://huggingface.co"
# A page that includes the full SideMenu JSON with all chapters:
COURSE_START = urljoin(BASE_URL, "/learn/agents-course/unit0/introduction")

OUTPUT_DIR = "ebooks"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def download_page(url):
    """Return the raw HTML of a URL."""
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.text

def parse_sidemenu_json(html_text):
    """
    1. Find the <div data-target="SideMenu" data-props="...">.
    2. Extract the JSON string from data-props.
    3. Parse and return the 'chapters' list.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    sidemenu_div = soup.find("div", {"data-target": "SideMenu"})
    if not sidemenu_div or not sidemenu_div.has_attr("data-props"):
        raise RuntimeError("Could not find the SideMenu data-props in the HTML.")

    # data-props is a JSON-like string, possibly with HTML entities we need to unescape
    raw_json_str = sidemenu_div["data-props"]
    raw_json_str = html.unescape(raw_json_str)  # decode any HTML entities

    props = json.loads(raw_json_str)
    if "chapters" not in props:
        raise RuntimeError("JSON from SideMenu does not have 'chapters'.")

    return props["chapters"]

def extract_gif_frames(gif_content, chapter_uid, img_counter, book):
    """
    Extract 8 key frames from a GIF and return HTML with the frames
    and the corresponding epub items.
    """
    try:
        frame_items = []
        frame_html = f'<div class="extracted-gif-frames"><h4>Extracted GIF Frames</h4>'
        
        with Image.open(BytesIO(gif_content)) as im:
            # Check if this is an animated GIF
            try:
                # For PIL version compatibility
                if hasattr(im, "is_animated") and not im.is_animated:
                    return None, []
                
                # Try to get the number of frames
                try:
                    n_frames = im.n_frames
                except AttributeError:
                    # Not animated or can't determine frames
                    return None, []
                
                if n_frames <= 1:
                    return None, []
                    
                num_key_frames = 8
                for i in range(num_key_frames):
                    try:
                        # Calculate frame index to get evenly distributed frames
                        frame_idx = max(0, min((n_frames // num_key_frames) * i, n_frames - 1))
                        im.seek(frame_idx)
                        
                        # Convert to RGB to ensure compatibility
                        frame = im.convert('RGB')
                        
                        # Save frame to a BytesIO object
                        frame_bytesio = BytesIO()
                        frame.save(frame_bytesio, format='JPEG')
                        frame_data = frame_bytesio.getvalue()
                        
                        # Create frame filename and epub item
                        frame_filename = f"images/{chapter_uid}_{img_counter}_frame{i}.jpg"
                        frame_item = epub.EpubItem(
                            uid=f"{chapter_uid}_img_{img_counter}_frame{i}",
                            file_name=frame_filename,
                            media_type="image/jpeg"
                        )
                        frame_item.set_content(frame_data)
                        book.add_item(frame_item)
                        frame_items.append(frame_item)
                        
                        # Add frame to HTML
                        frame_html += f'<img src="{frame_filename}" alt="GIF Frame {i}" style="margin: 5px; border: 1px solid #ccc;" />'
                        
                        if (i + 1) % 4 == 0:  # Add a line break every 4 images
                            frame_html += '<br/>'
                            
                    except Exception as e:
                        print(f"Error extracting frame {i} from GIF: {e}")
                        continue
            except Exception as e:
                print(f"Error determining if GIF is animated: {e}")
                return None, []
                    
        frame_html += '</div>'
        
        if not frame_items:
            return None, []
            
        return frame_html, frame_items
    except Exception as e:
        print(f"Error in extract_gif_frames: {e}")
        return None, []

def download_images_and_embed(book, soup, chapter_uid):
    """
    Find <img> tags in 'soup', download them, embed in EPUB as EpubItem,
    and rewrite <img src="..."> to the internal EPUB path so images display properly.
    For GIFs, extract 8 key frames and display them below the original image.
    """
    images = soup.find_all("img")
    img_counter = 0

    for img in images:
        src = img.get("src")
        if not src:
            continue

        full_url = urljoin(BASE_URL, src)
        try:
            r = requests.get(full_url)
            r.raise_for_status()
        except Exception as e:
            print(f"Failed to download image {full_url}: {e}")
            continue

        # Guess file extension & MIME type
        content_type = r.headers.get("Content-Type", "")
        if not content_type:
            ext = ".png"
            media_type = "image/png"
        else:
            main_type = content_type.split(";")[0].strip()
            ext = mimetypes.guess_extension(main_type) or ".png"
            # If the server returns something weird, default to image/png
            if not main_type.startswith("image/"):
                main_type = "image/png"
            media_type = main_type

        img_filename = f"images/{chapter_uid}_{img_counter}{ext}"
        img_counter += 1

        # Create an EpubItem for the image
        img_item = epub.EpubItem(
            uid=f"{chapter_uid}_img_{img_counter}",
            file_name=img_filename,
            media_type=media_type
        )
        img_item.set_content(r.content)

        book.add_item(img_item)

        # Update <img> tag src to the in-EPUB path
        img["src"] = img_filename
        
        # If this is a GIF, extract frames
        if ext.lower() == '.gif' or media_type.lower() == 'image/gif':
            print(f"Processing GIF: {full_url}")
            try:
                frames_html, frame_items = extract_gif_frames(r.content, chapter_uid, img_counter, book)
                if frames_html and frame_items:
                    # Instead of soup.new_tag, create a proper container with string HTML
                    # Create a container div
                    container_html = f'<div class="gif-container">{str(img)}{frames_html}</div>'
                    # Replace the img tag with the container that has both img and frames
                    new_soup = BeautifulSoup(container_html, 'html.parser')
                    img.replace_with(new_soup)
                    print(f"Successfully extracted {len(frame_items)} frames for {full_url}")
                else:
                    print(f"No frames extracted for {full_url}")
            except Exception as e:
                print(f"Failed to process GIF frames for {full_url}: {e}")

    return soup

def create_unit_epub(heading, subchapters):
    """
    Create a single EPUB for one "Unit" (or "Live", "Bonus", etc.) that bundles all subchapters.
    Each subchapter becomes a separate EpubHtml item in the spine.
    """
    book = epub.EpubBook()
    # Use the heading as metadata
    book.set_identifier(heading)
    book.set_title(heading)
    book.set_language("en")
    book.add_author("Hugging Face")

    # We'll store the EpubHtml chapters here
    chapter_items = []

    for idx, sc in enumerate(subchapters, start=1):
        sc_title = sc["title"]
        sc_url = sc["url"]
        print(f"   → Downloading subchapter: {sc_title} => {sc_url}")

        # Build the full URL, in case it's relative
        full_url = urljoin(BASE_URL, sc_url)
        try:
            sub_html = download_page(full_url)
        except Exception as e:
            print(f"      Failed to download {full_url}: {e}")
            continue

        soup = BeautifulSoup(sub_html, "html.parser")
        main_content = soup.find(class_="prose-doc")
        if not main_content:
            # fallback to entire page if .prose-doc not found
            main_content = soup

        # Embed images and handle GIFs
        chapter_uid = f"ch{idx}"
        main_content = download_images_and_embed(book, main_content, chapter_uid)

        # Create an EpubHtml item
        c = epub.EpubHtml(
            uid=chapter_uid,
            title=sc_title,
            file_name=f"chapter_{idx}.xhtml",
            lang="en"
        )
        c.set_content(str(main_content))
        book.add_item(c)
        chapter_items.append(c)

    if not chapter_items:
        print(f"   [!] No subchapters (or all failed) for {heading}, skipping EPUB creation.")
        return

    # Add navigation files
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Add CSS for styling extracted frames
    style = epub.EpubItem(
        uid="style",
        file_name="style/style.css",
        media_type="text/css",
        content="""
        .extracted-gif-frames {
            margin-top: 15px;
            padding: 10px;
            border: 1px dotted #ccc;
            background-color: #f9f9f9;
        }
        .extracted-gif-frames h4 {
            margin-top: 0;
            font-size: 1em;
            color: #666;
        }
        .gif-container {
            margin-bottom: 20px;
        }
        """
    )
    book.add_item(style)

    # Table of contents
    book.toc = chapter_items
    # Reading order
    book.spine = ["nav"] + chapter_items

    # Write the EPUB
    safe_heading = "".join(ch for ch in heading if ch.isalnum() or ch in " _-").strip()
    epub_filename = os.path.join(OUTPUT_DIR, f"{safe_heading}.epub")
    epub.write_epub(epub_filename, book, {})
    print(f"   [✔] Created EPUB: {epub_filename}\n")

def main():
    # 1) Download the base page
    base_html = download_page(COURSE_START)

    # 2) Parse the JSON in the SideMenu to get all chapters
    chapters_list = parse_sidemenu_json(base_html)

    # 3) For each chapter (e.g. "Unit 0. Welcome to the course"),
    #    gather all sections (subchapters) and build one EPUB
    for chapter in chapters_list:
        heading = chapter["title"]
        subchapters = chapter.get("sections", [])

        # If a chapter has no subchapters, we can skip or just create an empty book
        if not subchapters:
            print(f"Skipping '{heading}' because it has no subchapters.\n")
            continue

        print(f"Creating eBook for: {heading}")
        create_unit_epub(heading, subchapters)

if __name__ == "__main__":
    main()
