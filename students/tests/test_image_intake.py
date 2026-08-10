"""Pillow-only tests for the photo intake. No network, no API key, no database.

These cover the things that fail silently: a sideways photo still analyses,
just badly, and EXIF that survives is a privacy leak nobody sees.
"""
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from PIL import Image

from students.services.image_intake import (
    ImageIntakeError,
    encode_path_for_api,
    process_upload,
)


def jpeg(width, height, exif=None, colour="white"):
    buffer = io.BytesIO()
    kwargs = {"format": "JPEG", "quality": 90}
    if exif is not None:
        kwargs["exif"] = exif
    Image.new("RGB", (width, height), colour).save(buffer, **kwargs)
    buffer.seek(0)
    return buffer


def upload(width, height, name="working.jpg", **kw):
    return SimpleUploadedFile(name, jpeg(width, height, **kw).getvalue(), "image/jpeg")


def decode(b64):
    import base64
    return Image.open(io.BytesIO(base64.b64decode(b64)))


class ProcessUploadTests(SimpleTestCase):
    def test_downscales_and_keeps_aspect_ratio(self):
        _, w, h, _ = process_upload(upload(3000, 2000))
        self.assertEqual(max(w, h), 1600)
        self.assertAlmostEqual(w / h, 3000 / 2000, places=2)

    def test_small_enough_photo_is_left_alone(self):
        _, w, h, _ = process_upload(upload(1200, 900))
        self.assertEqual((w, h), (1200, 900))

    def test_rotates_by_exif_orientation(self):
        # Orientation 6 is a phone held in portrait: the pixels are landscape
        # and the tag says to turn them. Miss this and the model reads a
        # sideways page, then blames the handwriting.
        exif = Image.Exif()
        exif[274] = 6
        _, w, h, _ = process_upload(upload(400, 800, exif=exif))
        self.assertEqual((w, h), (800, 400))

    def test_strips_exif_including_gps(self):
        exif = Image.Exif()
        exif[274] = 1
        exif[34853] = {1: "N", 2: (53.0, 0.0, 0.0)}  # GPS
        content, _, _, _ = process_upload(upload(900, 900, exif=exif))
        out = Image.open(io.BytesIO(content.read()))
        self.assertFalse(dict(out.getexif()), "EXIF survived into the stored photo")

    def test_rejects_a_file_that_is_not_an_image(self):
        bad = SimpleUploadedFile("working.jpg", b"definitely not a jpeg", "image/jpeg")
        with self.assertRaises(ImageIntakeError):
            process_upload(bad)

    def test_rejects_a_photo_too_small_to_read(self):
        with self.assertRaises(ImageIntakeError):
            process_upload(upload(100, 100))

    @override_settings(WORK_PHOTO_MAX_BYTES=1024)
    def test_rejects_an_oversized_photo_before_decoding(self):
        big = upload(2000, 2000)
        with self.assertRaises(ImageIntakeError):
            process_upload(big)

    def test_heic_gets_its_own_message(self):
        heic = SimpleUploadedFile("IMG_1.heic", b"not really heic", "image/heic")
        with self.assertRaises(ImageIntakeError) as ctx:
            process_upload(heic)
        self.assertIn("HEIC", str(ctx.exception))

    def test_error_messages_are_written_for_students(self):
        # Nothing here should read like a stack trace.
        for bad in (upload(100, 100), SimpleUploadedFile("x.jpg", b"nope", "image/jpeg")):
            with self.assertRaises(ImageIntakeError) as ctx:
                process_upload(bad)
            message = str(ctx.exception)
            self.assertTrue(message[0].isupper(), message)
            for noise in ("Traceback", "Error:", "Exception", "None"):
                self.assertNotIn(noise, message)


class EncodeForApiTests(SimpleTestCase):
    def test_downscales_further_than_storage(self):
        # The stored copy is what the student sees; the API only needs enough
        # to read handwriting, and tiles at 512 anyway.
        out = decode(encode_path_for_api(jpeg(3000, 2000)))
        self.assertEqual(max(out.size), 1024)

    def test_applies_the_same_checks_as_upload(self):
        with self.assertRaises(ImageIntakeError):
            encode_path_for_api(jpeg(100, 100))
