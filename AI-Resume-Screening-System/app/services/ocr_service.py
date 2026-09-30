# ============================================================
#  TalentSync — OCR Fallback Service (GAP-14)
#  Image-only / scanned PDF optical character recognition fallback
#  with page ceilings, SSRF/DoS controls, and test isolation.
# ============================================================

import io
import re
from typing import Optional, Callable, List, Tuple
from PIL import Image
import PyPDF2
from app.config.settings import Config
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Test hook for isolated test environments where Tesseract binary is not installed
_mock_ocr_handler: Optional[Callable[[List[Image.Image]], str]] = None


def set_mock_ocr_handler(handler: Optional[Callable[[List[Image.Image]], str]]) -> None:
    """Register a custom handler for testing OCR flows without external binaries."""
    global _mock_ocr_handler
    _mock_ocr_handler = handler


def clear_mock_ocr_handler() -> None:
    """Clear any registered mock OCR handler."""
    global _mock_ocr_handler
    _mock_ocr_handler = None


def is_insufficient_text(text: str, min_chars: Optional[int] = None, min_words: int = 10) -> bool:
    """
    Determines whether text extracted via normal PDF parser is insufficient.
    Threshold: empty, under min_chars (default 50), under min_words (10),
    or lacking coherent alphanumeric words (>=3 consecutive letters).
    """
    if not text or not isinstance(text, str):
        return True

    cleaned = text.strip()
    limit = min_chars if min_chars is not None else Config.OCR_MIN_TEXT_CHARS

    if len(cleaned) < limit:
        return True

    words = cleaned.split()
    if len(words) < min_words:
        return True

    # Ensure text contains recognizable words rather than just garbage symbols or whitespace
    if re.search(r'[a-zA-Z]{3,}', cleaned) is None:
        return True

    return False


def is_ocr_engine_available() -> Tuple[bool, str]:
    """
    Checks if OCR is enabled and a functioning OCR engine is accessible.
    Returns (is_available, description).
    """
    if not Config.OCR_ENABLED:
        return False, "OCR is disabled in application configuration."

    if _mock_ocr_handler is not None:
        return True, "Mock OCR Test Engine Active"

    try:
        import pytesseract
        if Config.TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = Config.TESSERACT_CMD
        # Probe version to verify executable accessibility
        version = pytesseract.get_tesseract_version()
        return True, f"Tesseract OCR v{version}"
    except Exception as e:
        return False, f"Tesseract OCR engine not available on host: {e}"


def clean_ocr_text(raw_text: str) -> str:
    """
    Normalize raw OCR output to remove scanning artifacts, fix hyphenation,
    and unify multiple linebreaks.
    """
    if not raw_text:
        return ""

    # Replace null bytes and non-printable control chars
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw_text)
    # Fix broken hyphenated words across lines (e.g. "engi-\nneer" -> "engineer")
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    # Normalize consecutive blank lines to standard paragraph breaks
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Normalize multiple inline spaces
    text = re.sub(r'[ \t]{2,}', ' ', text)

    return text.strip()


def extract_images_from_pdf(file_stream, max_pages: int = 10) -> List[Image.Image]:
    """
    Extracts embedded raster images from PDF pages using PyPDF2.
    Robustly handles JPEG, PNG, and raw FlateDecode image streams.
    Safe resource limits: caps extracted pages to max_pages.
    """
    from PyPDF2.filters import _xobj_to_image

    images: List[Image.Image] = []
    if file_stream is None:
        return images

    try:
        if hasattr(file_stream, 'seek'):
            file_stream.seek(0)

        reader = PyPDF2.PdfReader(file_stream)
        total_pages = len(reader.pages) if reader.pages else 0
        pages_to_check = min(total_pages, max_pages)

        for p_idx in range(pages_to_check):
            page = reader.pages[p_idx]
            page_extracted = False

            # Primary: PyPDF2 page.images property
            try:
                for img_obj in page.images:
                    img_data = getattr(img_obj, 'data', None)
                    if img_data:
                        img = Image.open(io.BytesIO(img_data))
                        images.append(img)
                        page_extracted = True
            except Exception as img_err:
                logger.debug(f"PyPDF2 page.images warning on page {p_idx + 1}: {img_err}")

            # Secondary: Direct /Resources /XObject traversal for FlateDecode / uncompressed streams
            if not page_extracted:
                try:
                    res_dict = page.get('/Resources')
                    if res_dict:
                        res = res_dict.get_object() if hasattr(res_dict, 'get_object') else res_dict
                        if '/XObject' in res:
                            xobjs = res['/XObject']
                            xobjs = xobjs.get_object() if hasattr(xobjs, 'get_object') else xobjs
                            for name in xobjs:
                                raw_obj = xobjs[name]
                                deref = raw_obj.get_object() if hasattr(raw_obj, 'get_object') else raw_obj
                                if isinstance(deref, dict) and deref.get('/Subtype') == '/Image':
                                    ext, bstream = _xobj_to_image(deref)
                                    if bstream:
                                        if ext:
                                            img = Image.open(io.BytesIO(bstream))
                                        else:
                                            width = int(deref.get('/Width', 100))
                                            height = int(deref.get('/Height', 100))
                                            mode = 'RGB' if deref.get('/ColorSpace') == '/DeviceRGB' else 'L'
                                            img = Image.frombytes(mode, (width, height), bstream)
                                        images.append(img)
                except Exception as xobj_err:
                    logger.debug(f"Direct XObject extraction on page {p_idx + 1}: {xobj_err}")

    except Exception as e:
        logger.error(f"Failed to extract images from PDF for OCR: {e}")

    return images


def extract_text_via_ocr(file_stream, filename: str = "") -> dict:
    """
    Executes OCR fallback pipeline on a PDF file stream:
    1. Validates OCR engine availability
    2. Extracts images from the PDF up to OCR_MAX_PAGES
    3. Runs OCR engine (or test mock)
    4. Cleans and returns extracted text
    """
    available, reason = is_ocr_engine_available()
    if not available:
        logger.warning(f"OCR requested for '{filename}', but engine is unavailable: {reason}")
        return {
            "success": False,
            "raw_text": "",
            "ocr_applied": False,
            "pages_processed": 0,
            "images_processed": 0,
            "status": "UNAVAILABLE",
            "error": f"Image-based PDF detected, but OCR engine is not configured: {reason}"
        }

    max_pages = Config.OCR_MAX_PAGES
    images = extract_images_from_pdf(file_stream, max_pages=max_pages)

    if not images:
        logger.warning(f"No embedded images could be extracted from PDF '{filename}' for OCR.")
        return {
            "success": False,
            "raw_text": "",
            "ocr_applied": True,
            "pages_processed": 0,
            "images_processed": 0,
            "status": "NO_IMAGES",
            "error": "Image-based PDF detected, but no extractable image layers were found."
        }

    extracted_parts = []

    # Case 1: Mock handler registered for unit/integration tests
    if _mock_ocr_handler is not None:
        try:
            mock_text = _mock_ocr_handler(images)
            cleaned = clean_ocr_text(mock_text)
            return {
                "success": bool(cleaned),
                "raw_text": cleaned,
                "ocr_applied": True,
                "pages_processed": len(images),
                "images_processed": len(images),
                "status": "SUCCESS" if cleaned else "NO_TEXT_FOUND",
                "error": None if cleaned else "OCR could not detect readable text."
            }
        except Exception as e:
            return {
                "success": False,
                "raw_text": "",
                "ocr_applied": True,
                "pages_processed": 0,
                "images_processed": len(images),
                "status": "FAILED",
                "error": f"Mock OCR execution failed: {e}"
            }

    # Case 2: Production pytesseract execution
    try:
        import pytesseract
        for idx, img in enumerate(images):
            try:
                # Convert to RGB if palette/CMYK to ensure tesseract compatibility
                if img.mode not in ('L', 'RGB'):
                    img = img.convert('RGB')
                page_text = pytesseract.image_to_string(img)
                if page_text and page_text.strip():
                    extracted_parts.append(page_text.strip())
            except Exception as page_err:
                logger.error(f"OCR processing failed for image {idx + 1} in '{filename}': {page_err}")

        full_text = clean_ocr_text("\n\n".join(extracted_parts))
        success = bool(full_text and len(full_text) >= 10)

        return {
            "success": success,
            "raw_text": full_text,
            "ocr_applied": True,
            "pages_processed": len(images),
            "images_processed": len(images),
            "status": "SUCCESS" if success else "NO_TEXT_FOUND",
            "error": None if success else "OCR completed but found no readable text."
        }
    except Exception as e:
        logger.error(f"Pytesseract error on '{filename}': {e}")
        return {
            "success": False,
            "raw_text": "",
            "ocr_applied": True,
            "pages_processed": 0,
            "images_processed": len(images),
            "status": "FAILED",
            "error": f"OCR processing failed: {str(e)}"
        }
