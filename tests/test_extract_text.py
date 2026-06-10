"""Tests for extract_text — PDF, DOCX, image OCR, and text file extraction."""

from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from extract_text import (
    extract_file, extract_pdf, extract_docx, extract_image,
    IMAGE_EXTENSIONS, PDF_EXTENSIONS, DOCX_EXTENSIONS,
)


class TestExtensionSets:
    def test_pdf_extensions(self):
        assert ".pdf" in PDF_EXTENSIONS

    def test_docx_extensions(self):
        assert ".docx" in DOCX_EXTENSIONS

    def test_image_extensions(self):
        for ext in (".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp"):
            assert ext in IMAGE_EXTENSIONS


class TestExtractFile:
    def test_text_file(self, tmp_path):
        f = tmp_path / "notes.md"
        f.write_text("# Hello\nTest content.", encoding="utf-8")
        content, ftype = extract_file(f)
        assert ftype == "text"
        assert "Hello" in content

    def test_text_file_unknown_extension(self, tmp_path):
        f = tmp_path / "data.xyz"
        f.write_text("some text", encoding="utf-8")
        content, ftype = extract_file(f)
        assert ftype == "text"
        assert content == "some text"

    def test_file_not_found(self, tmp_path):
        content, ftype = extract_file(tmp_path / "nope.txt")
        assert ftype == "text"
        assert content == ""

    def test_extension_case_insensitive(self, tmp_path):
        f = tmp_path / "test.TXT"
        f.write_text("case check", encoding="utf-8")
        content, ftype = extract_file(f)
        assert ftype == "text"
        assert content == "case check"


class TestExtractPdf:
    def test_extract_pdf(self, tmp_path):
        from pypdf import PdfWriter
        pdf_path = tmp_path / "test.pdf"
        writer = PdfWriter()
        writer.add_blank_page(612, 792)
        writer.write(pdf_path)
        content = extract_pdf(pdf_path)
        assert isinstance(content, str)

    def test_missing_file(self, tmp_path):
        content = extract_pdf(tmp_path / "missing.pdf")
        assert content == ""

    def test_corrupt_file(self, tmp_path):
        f = tmp_path / "bad.pdf"
        f.write_bytes(b"not a real pdf")
        content = extract_pdf(f)
        assert content == ""


class TestExtractDocx:
    def test_extract_docx(self, tmp_path):
        from docx import Document
        docx_path = tmp_path / "test.docx"
        doc = Document()
        doc.add_paragraph("Hello from DOCX")
        doc.save(str(docx_path))
        content = extract_docx(docx_path)
        assert "Hello from DOCX" in content

    def test_missing_file(self, tmp_path):
        content = extract_docx(tmp_path / "missing.docx")
        assert content == ""

    def test_corrupt_file(self, tmp_path):
        f = tmp_path / "bad.docx"
        f.write_bytes(b"not a real docx")
        content = extract_docx(f)
        assert content == ""


class TestExtractImage:
    def test_extract_image_png(self, tmp_path):
        from PIL import Image, ImageDraw
        img_path = tmp_path / "test.png"
        img = Image.new("RGB", (200, 50), "white")
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "Hello OCR", fill="black")
        img.save(str(img_path))
        content = extract_image(img_path)
        assert isinstance(content, str)

    def test_extract_image_jpg(self, tmp_path):
        from PIL import Image, ImageDraw
        img_path = tmp_path / "test.jpg"
        img = Image.new("RGB", (200, 50), "white")
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "JPG Test", fill="black")
        img.save(str(img_path), "JPEG")
        content = extract_image(img_path)
        assert isinstance(content, str)

    def test_missing_file(self, tmp_path):
        content = extract_image(tmp_path / "missing.png")
        assert content == ""

    def test_corrupt_file(self, tmp_path):
        f = tmp_path / "bad.png"
        f.write_bytes(b"not an image")
        content = extract_image(f)
        assert content == ""

    def test_empty_image(self, tmp_path):
        from PIL import Image
        img_path = tmp_path / "blank.png"
        img = Image.new("RGB", (10, 10), "white")
        img.save(str(img_path))
        content = extract_image(img_path)
        assert isinstance(content, str)


class TestExtractFileDispatch:
    def test_dispatch_pdf(self, tmp_path):
        f = tmp_path / "doc.pdf"
        f.write_text("dummy", encoding="utf-8")
        content, ftype = extract_file(f)
        assert ftype == "pdf"

    def test_dispatch_docx(self, tmp_path):
        f = tmp_path / "doc.docx"
        f.write_text("dummy", encoding="utf-8")
        content, ftype = extract_file(f)
        assert ftype == "docx"

    def test_dispatch_image(self, tmp_path):
        f = tmp_path / "photo.jpg"
        f.write_text("dummy", encoding="utf-8")
        content, ftype = extract_file(f)
        assert ftype == "image"

    def test_dispatch_heic(self, tmp_path):
        f = tmp_path / "photo.heic"
        f.write_text("dummy", encoding="utf-8")
        content, ftype = extract_file(f)
        assert ftype == "image"

    def test_dispatch_text(self, tmp_path):
        f = tmp_path / "readme.md"
        f.write_text("content", encoding="utf-8")
        content, ftype = extract_file(f)
        assert ftype == "text"
        assert content == "content"
