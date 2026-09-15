"""Turning a phone photo of a student's copy into something safe to store and send.

A photo off a phone is not usable as-is. It arrives rotated (the camera records
orientation in EXIF rather than rotating the pixels), carrying GPS coordinates,
and at a resolution far beyond anything the vision API reads. Every function
here exists to fix one of those.

Nothing in this module touches the network or the database, which is what makes
it the easy part of the feature to test.
"""
import io
import logging

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger(__name__)

# Below this the handwriting is not legible to the model either, so it is
# kinder to say so than to spend a call finding out.
MIN_LONG_EDGE = 400


class ImageIntakeError(Exception):
    """A rejection with a message that is safe to show a student.

    Anything raised as this is written for the student to read. Internal
    failures must not be wrapped in it.
    """


def _open_verified(file_obj):
    """Decode an upload, trusting the bytes rather than the declared type.

    ``content_type`` comes from the client and means nothing. ``verify()``
    checks the file really is an image, but leaves the object unusable, so the
    caller has to reopen -- hence the two passes.
    """
    try:
        file_obj.seek(0)
        Image.open(file_obj).verify()
        file_obj.seek(0)
        return Image.open(file_obj)
    except UnidentifiedImageError:
        name = (getattr(file_obj, "name", "") or "").lower()
        if name.endswith((".heic", ".heif")):
            raise ImageIntakeError(
                "Your iPhone saved this as HEIC, which we can't read. Use the "
                "camera button on this page rather than picking a file, or set "
                "Settings → Camera → Formats → Most Compatible."
            )
        raise ImageIntakeError("That doesn't look like a photo. Try again with a JPEG or PNG.")
    except Exception:
        logger.exception("Unreadable upload")
        raise ImageIntakeError("We couldn't open that file. Try taking the photo again.")


def _prepare(source):
    """Open, verify, rotate upright and check legibility.

    Both entry points go through here, so a photo taken off disk by the probe
    gets exactly the checks an uploaded one does.
    """
    if not hasattr(source, "read"):
        source = open(source, "rb")
    img = _normalise(_open_verified(source))
    if max(img.width, img.height) < MIN_LONG_EDGE:
        raise ImageIntakeError("That photo is too small to read. Take it a bit closer.")
    return img


def _normalise(img):
    """Rotate upright, drop metadata, and flatten to RGB.

    ``exif_transpose`` is the important line. Phones almost never rotate the
    pixels; they set an orientation tag and leave it to the viewer. Skip this
    and a sideways page reaches the model, which reads it badly and blames the
    handwriting.

    It also drops the orientation tag, and rebuilding the image through
    ``convert`` leaves the rest of the EXIF -- GPS included -- behind.
    """
    img = ImageOps.exif_transpose(img)
    return img.convert("RGB")


def _to_jpeg(img, max_edge, quality=85):
    img.thumbnail((max_edge, max_edge), Image.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue(), img.width, img.height


def process_upload(uploaded_file):
    """Validate and normalise a student's photo, ready to store.

    Returns ``(ContentFile, width, height, byte_size)``.
    Raises ``ImageIntakeError`` with student-facing wording on rejection.
    """
    max_bytes = getattr(settings, "WORK_PHOTO_MAX_BYTES", 8 * 1024 * 1024)
    size = getattr(uploaded_file, "size", None)

    # Checked before decoding, so a huge file is refused without being read.
    if size and size > max_bytes:
        raise ImageIntakeError(
            "That photo is too large. Use the camera button on this page, "
            "which shrinks it for you."
        )

    img = _prepare(uploaded_file)

    max_edge = getattr(settings, "WORK_PHOTO_STORE_MAX_EDGE", 1600)
    data, width, height = _to_jpeg(img, max_edge)
    return ContentFile(data), width, height, len(data)


# ---------------------------------------------------------------------------
# Scanned PDFs
#
# A scan arrives as one PDF of several pages rather than one photo per page.
# Each page is rendered and then stored exactly as a photo would be, so nothing
# downstream -- the vision call, the report, the purge -- can tell them apart.
# process_upload above is left alone: the student photo path depends on it.
# ---------------------------------------------------------------------------

# A4 at 150 DPI is about 1750px on the long edge, just above the 1600px store
# size. More would only be thrown away by the downscale that follows.
PDF_RENDER_DPI = 150


def is_pdf(data):
    """True if the bytes are a PDF. The spec allows the header anywhere in the
    first 1024 bytes, and filenames and declared types mean nothing."""
    return b"%PDF-" in bytes(data[:1024])


def _open_pdf(data):
    import fitz  # PyMuPDF; imported here so photo-only callers never load it

    try:
        doc = fitz.open(stream=bytes(data), filetype="pdf")
    except Exception:
        raise ImageIntakeError("That PDF couldn't be opened. Try scanning it again.")
    if doc.needs_pass:
        doc.close()
        raise ImageIntakeError(
            "That PDF is password-protected, so it can't be read. Scan it again "
            "without a password.")
    if doc.page_count == 0:
        doc.close()
        raise ImageIntakeError("That PDF has no pages.")
    return doc


def _render_pdf_page(doc, index, dpi=PDF_RENDER_DPI):
    try:
        pix = doc[index].get_pixmap(dpi=dpi, alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    except Exception:
        logger.exception("Could not render page %s of a scanned PDF", index + 1)
        raise ImageIntakeError(
            f"Page {index + 1} of that PDF couldn't be read. Try scanning it again.")


def pdf_page_count(data):
    """Pages in a PDF, raising ImageIntakeError if it can't be read."""
    doc = _open_pdf(data)
    try:
        return doc.page_count
    finally:
        doc.close()


def pdf_thumbnail(data, max_edge=900):
    """The first page as a JPEG, big enough to read the name written on it."""
    doc = _open_pdf(data)
    try:
        img, _, _ = _to_jpeg(_render_pdf_page(doc, 0), max_edge)
        return ContentFile(img)
    finally:
        doc.close()


def process_pdf_pages(data, max_pages):
    """Every page of a scanned PDF, ready to store as photos.

    Returns a list of ``(ContentFile, width, height, byte_size)``, the same
    shape ``process_upload`` gives for one photo. Raises ``ImageIntakeError``
    with wording a teacher can act on.
    """
    doc = _open_pdf(data)
    try:
        if doc.page_count > max_pages:
            raise ImageIntakeError(
                f"That PDF has {doc.page_count} pages, and a check takes at most "
                f"{max_pages}. Scan single-sided, or split it.")
        max_edge = getattr(settings, "WORK_PHOTO_STORE_MAX_EDGE", 1600)
        pages = []
        for index in range(doc.page_count):
            img, width, height = _to_jpeg(_render_pdf_page(doc, index), max_edge)
            pages.append((ContentFile(img), width, height, len(img)))
        return pages
    finally:
        doc.close()


def encode_for_api(image_field, max_edge=None):
    """Base64 a stored photo, downscaled again for the vision call.

    Deliberately smaller than the stored copy. The student gets shown the
    stored one; the model only needs enough to read handwriting.
    """
    if max_edge is None:
        max_edge = getattr(settings, "WORK_PHOTO_API_MAX_EDGE", 1024)
    with image_field.open("rb") as fh:
        return encode_path_for_api(fh, max_edge)


def encode_path_for_api(source, max_edge=None):
    """As ``encode_for_api``, but for a path or open file rather than a field.

    This is what lets the probe command run against a photo on disk with no
    model, no storage and no upload in the way.
    """
    import base64

    if max_edge is None:
        max_edge = getattr(settings, "WORK_PHOTO_API_MAX_EDGE", 1024)
    data, _, _ = _to_jpeg(_prepare(source), max_edge)
    return base64.b64encode(data).decode("utf-8")
