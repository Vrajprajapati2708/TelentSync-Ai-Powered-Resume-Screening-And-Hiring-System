import io
import uuid
import time
from datetime import datetime
import PyPDF2
from PyPDF2.errors import PdfReadError
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Parser Configuration
PARSER_CONFIG = {
    "max_pages": 100,
    "max_file_size": 10 * 1024 * 1024,
    "encoding": "utf-8",
    "parser_version": "v1.0"
}

# Parser Status Constants
class ParseStatus:
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    UNSUPPORTED = "UNSUPPORTED"


def extract_pdf_with_metadata(file, filename: str = "") -> dict:
    """
    Extract text and layout metadata from a PDF file object with robust error handling.
    """
    t_start = time.time()
    errors = []
    clean_name = filename or getattr(file, 'filename', '') or 'document.pdf'

    logger.info(f"START PARSE [PDF]: filename='{clean_name}'")

    if file is None:
        logger.warning("extract_pdf_with_metadata received None file object.")
        duration_ms = int((time.time() - t_start) * 1000)
        return _build_pdf_result(False, "", clean_name, 0, 0, 0, 0, ["File object is None."], duration_ms, ParseStatus.FAILED)

    # Calculate stream size safely
    file_size = 0
    try:
        if hasattr(file, 'seek') and hasattr(file, 'tell'):
            file.seek(0, 2)
            file_size = file.tell()
            file.seek(0)
    except Exception:
        file_size = 0

    try:
        if hasattr(file, 'seek'):
            file.seek(0)

        pdf_reader = PyPDF2.PdfReader(file)
        page_count = len(pdf_reader.pages) if pdf_reader.pages else 0

        if page_count == 0:
            msg = "PyPDF2 read 0 pages from PDF file."
            logger.warning(msg)
            duration_ms = int((time.time() - t_start) * 1000)
            return _build_pdf_result(False, "", clean_name, file_size, 0, 0, 0, [msg], duration_ms, ParseStatus.FAILED)

        pages_text = []

        for page_num, page in enumerate(pdf_reader.pages):
            if page_num >= PARSER_CONFIG["max_pages"]:
                logger.warning(f"Exceeded max page ceiling of {PARSER_CONFIG['max_pages']} pages.")
                break
            try:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    pages_text.append(page_text.strip())
                else:
                    logger.warning(f"Page {page_num + 1} returned no text (may be image-based or blank).")
            except Exception as page_err:
                err_msg = f"Error extracting text on page {page_num + 1}: {page_err}"
                logger.error(err_msg)
                errors.append(err_msg)

        full_text = "\n\n".join(pages_text).strip()
        word_count = len(full_text.split())
        char_count = len(full_text)
        duration_ms = int((time.time() - t_start) * 1000)

        from app.services.ocr_service import is_insufficient_text, extract_text_via_ocr

        ocr_applied = False
        parser_name = "PyPDF2"

        if is_insufficient_text(full_text):
            logger.info(f"Normal extraction returned insufficient text ({len(full_text)} chars) for '{clean_name}'. Invoking OCR fallback...")
            ocr_result = extract_text_via_ocr(file, clean_name)
            if ocr_result["success"] and ocr_result["raw_text"]:
                full_text = ocr_result["raw_text"]
                word_count = len(full_text.split())
                char_count = len(full_text)
                ocr_applied = True
                parser_name = "OCR Fallback (PyPDF2 + Tesseract)"
                logger.info(f"OCR fallback succeeded for '{clean_name}': {word_count} words extracted.")
            elif full_text and len(full_text.strip()) >= 10:
                # Retain normal text if OCR cannot extract better text
                logger.info(f"OCR not applied; retaining normally extracted text ({len(full_text)} chars) for '{clean_name}'.")
            else:
                ocr_err = ocr_result.get("error") or "Could not extract text from PDF. File may be an image-based scan or corrupt."
                logger.warning(f"OCR fallback unable to extract text for '{clean_name}': {ocr_err}")
                duration_ms = int((time.time() - t_start) * 1000)
                return _build_pdf_result(False, "", clean_name, file_size, page_count, 0, 0, [ocr_err], duration_ms, ParseStatus.FAILED, parser_name="OCR Fallback", ocr_applied=ocr_result.get("ocr_applied", False))


        status = ParseStatus.PARTIAL if errors else ParseStatus.SUCCESS
        logger.info(f"PARSED [PDF]: status={status} | parser={parser_name} | duration={duration_ms}ms | pages={page_count} | words={word_count}")

        return _build_pdf_result(True, full_text, clean_name, file_size, page_count, word_count, char_count, errors, duration_ms, status, parser_name=parser_name, ocr_applied=ocr_applied)

    except PdfReadError as e:
        duration_ms = int((time.time() - t_start) * 1000)
        err_msg = f"PyPDF2 corrupt PDF error: {str(e)}"
        logger.error(f"PARSED FAILED [PDF]: duration={duration_ms}ms | error={err_msg}")
        return _build_pdf_result(False, "", clean_name, file_size, 0, 0, 0, [err_msg], duration_ms, ParseStatus.FAILED)
    except Exception as e:
        duration_ms = int((time.time() - t_start) * 1000)
        err_msg = f"Unexpected PDF parsing failure: {str(e)}"
        logger.error(f"PARSED FAILED [PDF]: duration={duration_ms}ms | error={err_msg}")
        return _build_pdf_result(False, "", clean_name, file_size, 0, 0, 0, [err_msg], duration_ms, ParseStatus.FAILED)


def extract_text_from_pdf(file) -> str:
    """
    Backward-compatible wrapper: extracts text from PDF and returns lowercased string.
    """
    res = extract_pdf_with_metadata(file)
    return res['raw_text'].lower() if res['success'] else ""


def extract_text_from_bytes(file_bytes: bytes) -> str:
    """Convenience wrapper: accepts raw bytes instead of a file object."""
    return extract_text_from_pdf(io.BytesIO(file_bytes))


def _build_pdf_result(
    success: bool,
    raw_text: str,
    filename: str,
    size: int,
    pages: int,
    words: int,
    chars: int,
    errors: list,
    duration_ms: int = 0,
    status: str = ParseStatus.SUCCESS,
    parser_name: str = "PyPDF2",
    ocr_applied: bool = False
) -> dict:
    """Helper to construct standardized PDF parser result structure."""
    return {
        'success': success,
        'raw_text': raw_text,
        'metadata': {
            'document_id': f"doc_{uuid.uuid4().hex[:12]}",
            'file_name': filename,
            'file_type': 'pdf',
            'encoding': PARSER_CONFIG["encoding"],
            'file_size_bytes': size,
            'page_count': pages,
            'word_count': words,
            'character_count': chars,
            'language': 'en',
            'parser_name': parser_name,
            'parser_version': PARSER_CONFIG["parser_version"],
            'ocr_applied': ocr_applied,
            'parser_duration_ms': duration_ms,
            'processing_time_ms': duration_ms,
            'created_at': datetime.now().isoformat(),
            'parse_status': status,
            'parse_errors': errors
        },
        'errors': errors
    }



