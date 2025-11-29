# exam_papers/utils.py
"""
Utilities for processing exam paper PDFs and extracting question images.
"""
import fitz  # PyMuPDF
from PIL import Image
import io
import os
from django.core.files.base import ContentFile


def extract_pdf_pages_as_images(pdf_path, output_dir=None, dpi=200):
    """
    Extract each page of a PDF as a high-quality image.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save images (optional)
        dpi: Resolution for image extraction (default 200)

    Returns:
        List of tuples (page_number, image_bytes)
    """
    doc = fitz.open(pdf_path)
    images = []

    # Calculate zoom for desired DPI (72 is default PDF DPI)
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=mat)

        # Convert to PIL Image
        img_data = pix.tobytes("png")

        # Optionally save to file
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            filename = f"page_{page_num + 1}.png"
            filepath = os.path.join(output_dir, filename)
            pix.save(filepath)

        images.append((page_num + 1, img_data))

    doc.close()
    return images


def split_pdf_into_questions(pdf_path, num_questions, output_dir=None):
    """
    Split a PDF into individual question images.
    Assumes questions are distributed evenly across pages.

    Args:
        pdf_path: Path to the PDF file
        num_questions: Number of questions in the paper
        output_dir: Directory to save question images (optional)

    Returns:
        List of tuples (question_number, image_bytes)
    """
    # First, extract all pages
    pages = extract_pdf_pages_as_images(pdf_path)

    # Calculate pages per question (rough approximation)
    total_pages = len(pages)
    pages_per_question = total_pages / num_questions

    question_images = []

    for q_num in range(1, num_questions + 1):
        # Determine which page(s) this question is likely on
        start_page = int((q_num - 1) * pages_per_question)
        end_page = int(q_num * pages_per_question)

        # For now, just take the first page of each question
        # (Can be enhanced to combine multiple pages)
        if start_page < len(pages):
            page_num, img_data = pages[start_page]

            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                filename = f"question_{q_num}.png"
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(img_data)

            question_images.append((q_num, img_data))

    return question_images


def extract_pdf_page_ranges(pdf_path, page_ranges, output_dir=None):
    """
    Extract specific page ranges from PDF as images.
    More precise than automatic splitting.

    Args:
        pdf_path: Path to the PDF file
        page_ranges: List of tuples (question_num, start_page, end_page)
                    Example: [(1, 1, 1), (2, 2, 3), (3, 4, 4)]
        output_dir: Directory to save images (optional)

    Returns:
        List of tuples (question_number, image_bytes)
    """
    doc = fitz.open(pdf_path)
    question_images = []

    dpi = 200
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    for question_num, start_page, end_page in page_ranges:
        # If single page, just extract that page
        if start_page == end_page:
            page = doc[start_page - 1]  # 0-indexed
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")

            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                filename = f"question_{question_num}.png"
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(img_data)

            question_images.append((question_num, img_data))
        else:
            # Multiple pages - combine them vertically
            images_to_combine = []
            for page_num in range(start_page - 1, end_page):
                page = doc[page_num]
                pix = page.get_pixmap(matrix=mat)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                images_to_combine.append(img)

            # Combine images vertically
            total_width = images_to_combine[0].width
            total_height = sum(img.height for img in images_to_combine)

            combined = Image.new('RGB', (total_width, total_height))
            y_offset = 0
            for img in images_to_combine:
                combined.paste(img, (0, y_offset))
                y_offset += img.height

            # Save combined image
            img_buffer = io.BytesIO()
            combined.save(img_buffer, format='PNG')
            img_data = img_buffer.getvalue()

            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                filename = f"question_{question_num}.png"
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(img_data)

            question_images.append((question_num, img_data))

    doc.close()
    return question_images


def get_pdf_info(pdf_path):
    """
    Get basic information about a PDF file.

    Returns:
        dict with page_count, dimensions, etc.
    """
    doc = fitz.open(pdf_path)
    info = {
        'page_count': len(doc),
        'metadata': doc.metadata,
        'pages': []
    }

    for page_num in range(len(doc)):
        page = doc[page_num]
        info['pages'].append({
            'number': page_num + 1,
            'width': page.rect.width,
            'height': page.rect.height
        })

    doc.close()
    return info