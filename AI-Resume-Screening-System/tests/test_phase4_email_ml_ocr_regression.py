# ============================================================
#  HireAI / TalentSync — Phase 4 Regression Test Suite
#  Covers:
#    GAP-12: Email Subsystem & Token Security
#    GAP-13: ML Dependency & Model Hardening
#    GAP-14: OCR Fallback for Scanned / Image-Only PDFs
# ============================================================

import os
import sys
import io
import time
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

_APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

from app import create_app
from app.config.settings import Config, ProductionConfig, TestingConfig
from app.database.connection import get_db
from app.controllers.auth_controller import (
    register_user,
    generate_email_verification_token,
    verify_email_token,
    generate_password_reset_token,
    reset_password_with_token
)
from app.services.email_service import (
    EmailMessage,
    TestEmailProvider,
    SMTPEmailProvider,
    get_email_provider,
    send_verification_email,
    send_password_reset_email
)
from app.services.ocr_service import (
    is_insufficient_text,
    is_ocr_engine_available,
    clean_ocr_text,
    extract_text_via_ocr,
    set_mock_ocr_handler,
    clear_mock_ocr_handler
)
from app.ml.parsers.pdf_parser import extract_pdf_with_metadata, extract_text_from_pdf
from app.ml.resume_intelligence.resume_json_builder import build_resume_intelligence


def _create_synthetic_scanned_pdf(text_content: str) -> io.BytesIO:
    """
    Creates a synthetic image-only PDF containing rasterized text.
    PyPDF2 text extraction will yield 0 text, but the page contains an embedded image.
    """
    from reportlab.pdfgen import canvas
    from PIL import Image, ImageDraw

    # 1. Render text into a raster image
    img = Image.new("RGB", (600, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), text_content, fill=(0, 0, 0))

    tf = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img.save(tf.name)
    tf.close()

    # 2. Draw image into PDF without any text elements
    pdf_buf = io.BytesIO()
    c = canvas.Canvas(pdf_buf, pagesize=(600, 400))
    c.drawImage(tf.name, 0, 0, width=600, height=400)
    c.showPage()
    c.save()

    try:
        os.unlink(tf.name)
    except Exception:
        pass

    pdf_buf.seek(0)
    return pdf_buf


def _create_synthetic_text_pdf(text_content: str) -> io.BytesIO:
    """Creates a standard text-based PDF where PyPDF2 extracts text normally."""
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    text_object = c.beginText(40, 750)
    for line in text_content.split("\n"):
        text_object.textLine(line)
    c.drawText(text_object)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf


class SafeProductionConfig(ProductionConfig):
    """Production configuration with test email delivery to prevent SMTP socket timeouts."""
    MAIL_PROVIDER = "test"
    DB_FILE = TestingConfig.DB_FILE
    UPLOAD_FOLDER = TestingConfig.UPLOAD_FOLDER


class TestPhase4EmailMlOcrRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(TestingConfig)

    def setUp(self):
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        TestEmailProvider.clear_outbox()
        clear_mock_ocr_handler()

    def tearDown(self):
        TestEmailProvider.clear_outbox()
        clear_mock_ocr_handler()
        self.app_context.pop()

    # ============================================================
    # GAP-12: Email Subsystem & Token Security Tests
    # ============================================================

    def test_gap12_registration_dispatches_verification_email(self):
        """User registration sends a verification email to the recipient with a secure link."""
        email = f"test_reg_{int(time.time()*1000)}@test.com"
        res = self.client.post("/api/auth/register", json={
            "name": "Alex Morgan",
            "email": email,
            "password": "ValidPassword10!",
            "role": "candidate"
        })
        self.assertEqual(res.status_code, 201)

        outbox = TestEmailProvider.get_outbox()
        self.assertGreaterEqual(len(outbox), 1)
        last_email = outbox[-1]
        self.assertEqual(last_email.to_email, email)
        self.assertIn("Verify your TalentSync account", last_email.subject)
        self.assertIn("#page-verify?token=", last_email.text_body)
        self.assertIn("24 hours", last_email.text_body)

    def test_gap12_production_tokens_not_exposed_in_registration_response(self):
        """In production mode, registration response does NOT expose verification token."""
        prod_app = create_app(SafeProductionConfig)
        with prod_app.app_context():
            client = prod_app.test_client()
            email = f"prod_reg_{int(time.time()*1000)}@test.com"
            res = client.post("/api/auth/register", json={
                "name": "Prod User",
                "email": email,
                "password": "ValidPassword10!",
                "role": "candidate"
            })
            self.assertEqual(res.status_code, 201)
            data = res.get_json()
            self.assertNotIn("dev_verification_token", data)
            self.assertNotIn("token", data)
            self.assertNotIn("raw_token", data)


    def test_gap12_email_verification_success(self):
        """Valid token successfully verifies account."""
        email = f"verify_ok_{int(time.time()*1000)}@test.com"
        cand_id = register_user("Verify Cand", email, "ValidPassword10!", "candidate")["user"]["id"]
        token = generate_email_verification_token(cand_id)

        res = self.client.post("/api/auth/verify_email", json={"token": token})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json().get("success"))

        with get_db() as conn:
            user = conn.execute("SELECT is_verified FROM users WHERE id=?", (cand_id,)).fetchone()
            self.assertEqual(user["is_verified"], 1)

    def test_gap12_email_verification_invalid_token_rejected(self):
        """Invalid token is safely rejected with HTTP 400."""
        res = self.client.post("/api/auth/verify_email", json={"token": "invalid_token_12345"})
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.get_json().get("success"))

    def test_gap12_email_verification_token_reuse_rejected(self):
        """Used token cannot be reused a second time."""
        email = f"verify_reuse_{int(time.time()*1000)}@test.com"
        cand_id = register_user("Reuse Cand", email, "ValidPassword10!", "candidate")["user"]["id"]
        token = generate_email_verification_token(cand_id)

        res1 = self.client.post("/api/auth/verify_email", json={"token": token})
        self.assertEqual(res1.status_code, 200)

        res2 = self.client.post("/api/auth/verify_email", json={"token": token})
        self.assertEqual(res2.status_code, 400)
        self.assertIn("Invalid or expired", res2.get_json().get("message", ""))

    def test_gap12_email_verification_expired_token_rejected(self):
        """Expired verification token is rejected."""
        email = f"verify_exp_{int(time.time()*1000)}@test.com"
        cand_id = register_user("Exp Cand", email, "ValidPassword10!", "candidate")["user"]["id"]
        token = generate_email_verification_token(cand_id)

        # Force token expiration in database
        yesterday = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
        with get_db() as conn:
            conn.execute("UPDATE email_verification_tokens SET expires_at=? WHERE user_id=?", (yesterday, cand_id))
            conn.commit()

        res = self.client.post("/api/auth/verify_email", json={"token": token})
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.get_json().get("success"))

    def test_gap12_resend_verification_sends_email_and_invalidates_prior(self):
        """Resend verification sends new email and invalidates previous token."""
        email = f"resend_{int(time.time()*1000)}@test.com"
        cand_id = register_user("Resend Cand", email, "ValidPassword10!", "candidate")["user"]["id"]

        TestEmailProvider.clear_outbox()
        res = self.client.post("/api/auth/resend_verification", json={"email": email})
        self.assertEqual(res.status_code, 200)

        outbox = TestEmailProvider.get_outbox()
        self.assertEqual(len(outbox), 1)
        self.assertEqual(outbox[0].to_email, email)

        # Verify old token is marked as used/invalidated
        with get_db() as conn:
            tokens = conn.execute("SELECT is_used FROM email_verification_tokens WHERE user_id=? ORDER BY id ASC", (cand_id,)).fetchall()
            self.assertEqual(len(tokens), 2)
            self.assertEqual(tokens[0]["is_used"], 1)  # First token invalidated
            self.assertEqual(tokens[1]["is_used"], 0)  # New token active

    def test_gap12_forgot_password_dispatches_reset_email(self):
        """Forgot password dispatches secure reset email to user."""
        email = f"forgot_{int(time.time()*1000)}@test.com"
        register_user("Forgot Cand", email, "ValidPassword10!", "candidate")

        TestEmailProvider.clear_outbox()
        res = self.client.post("/api/auth/forgot_password", json={"email": email})
        self.assertEqual(res.status_code, 200)

        outbox = TestEmailProvider.get_outbox()
        self.assertEqual(len(outbox), 1)
        last_email = outbox[-1]
        self.assertEqual(last_email.to_email, email)
        self.assertIn("Reset your TalentSync password", last_email.subject)
        self.assertIn("#page-reset?token=", last_email.text_body)
        self.assertIn("15 minutes", last_email.text_body)

    def test_gap12_forgot_password_anti_enumeration(self):
        """Forgot password returns identical generic response for nonexistent email."""
        nonexistent = f"ghost_{int(time.time()*1000)}@test.com"
        res = self.client.post("/api/auth/forgot_password", json={"email": nonexistent})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("If an account with that email exists", data.get("message", ""))

    def test_gap12_production_tokens_not_exposed_in_password_reset_response(self):
        """In production mode, forgot_password response does NOT leak reset token."""
        prod_app = create_app(SafeProductionConfig)
        with prod_app.app_context():
            client = prod_app.test_client()
            email = f"prod_forgot_{int(time.time()*1000)}@test.com"
            register_user("Prod Reset", email, "ValidPassword10!", "candidate")

            res = client.post("/api/auth/forgot_password", json={"email": email})
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertNotIn("dev_reset_token", data)
            self.assertNotIn("token", data)

    def test_gap12_password_reset_success(self):
        """Valid reset token successfully changes user password."""
        email = f"reset_ok_{int(time.time()*1000)}@test.com"
        cand_id = register_user("Reset Success", email, "OldPassword10!", "candidate", is_verified=1)["user"]["id"]
        token_data = generate_password_reset_token(email)

        # Extract raw token from dispatched test email
        last_email = TestEmailProvider.get_last_email()
        raw_token = last_email.text_body.split("token=")[1].split()[0]

        res = self.client.post("/api/auth/reset_password", json={
            "token": raw_token,
            "new_password": "NewSecurePassword10!"
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json().get("success"))

        # Verify login succeeds with new password
        login_res = self.client.post("/api/auth/login", json={
            "email": email,
            "password": "NewSecurePassword10!"
        })
        self.assertEqual(login_res.status_code, 200)
        self.assertTrue(login_res.get_json().get("success"))

    def test_gap12_password_reset_rejects_under_10_chars(self):
        """Password reset rejects passwords under 10 characters."""
        email = f"reset_short_{int(time.time()*1000)}@test.com"
        register_user("Short Reset", email, "ValidPassword10!", "candidate")
        generate_password_reset_token(email)
        raw_token = TestEmailProvider.get_last_email().text_body.split("token=")[1].split()[0]

        res = self.client.post("/api/auth/reset_password", json={
            "token": raw_token,
            "new_password": "Short1!"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("at least 10 characters", res.get_json().get("message", ""))

    def test_gap12_password_reset_token_reuse_prevented(self):
        """Used reset token cannot be used twice."""
        email = f"reset_reuse_{int(time.time()*1000)}@test.com"
        register_user("Reuse Reset", email, "ValidPassword10!", "candidate")
        generate_password_reset_token(email)
        raw_token = TestEmailProvider.get_last_email().text_body.split("token=")[1].split()[0]

        res1 = self.client.post("/api/auth/reset_password", json={"token": raw_token, "new_password": "NewPassword10!"})
        self.assertEqual(res1.status_code, 200)

        res2 = self.client.post("/api/auth/reset_password", json={"token": raw_token, "new_password": "AnotherPassword10!"})
        self.assertEqual(res2.status_code, 400)
        self.assertIn("Invalid or expired", res2.get_json().get("message", ""))

    def test_gap12_smtp_provider_failure_handling(self):
        """Simulate SMTP provider connection failure without throwing unhandled exceptions."""
        failing_provider = SMTPEmailProvider(host="invalid.nonexistent.smtp.host", port=9999, timeout=1)
        msg = EmailMessage(
            to_email="failure_test@test.com",
            subject="Failure Test",
            text_body="Test",
            html_body="<p>Test</p>"
        )
        success = failing_provider.send(msg)
        self.assertFalse(success)

    # ============================================================
    # GAP-13: ML Dependency & Model Hardening Tests
    # ============================================================

    def test_gap13_ml_status_endpoint_structure(self):
        """GET /api/ml/status returns version info, health, and sanitized relative paths."""
        res = self.client.get("/api/ml/status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertIn("health", data)
        self.assertIn("version_info", data)
        self.assertIn("models_loaded", data)
        self.assertIn("models", data)

        version_info = data["version_info"]
        self.assertIn("scikit_learn", version_info)
        self.assertIn("spacy", version_info)
        self.assertIn("numpy", version_info)

        # Ensure absolute host filesystem paths are masked
        spacy_path = data["models"]["spacy_ner"]["path"]
        tfidf_path = data["models"]["tfidf_recommender"]["path"]
        self.assertFalse(spacy_path.startswith("C:\\") or spacy_path.startswith("V:\\"))
        self.assertFalse(tfidf_path.startswith("C:\\") or tfidf_path.startswith("V:\\"))

    def test_gap13_tfidf_model_loads_and_scores_cleanly(self):
        """TF-IDF recommender vectorizer computes similarity without deprecation crash."""
        from app.ml.recommendation.tfidf_model import TFIDFVectorizer, is_sklearn_available
        self.assertTrue(is_sklearn_available())

        vec = TFIDFVectorizer()
        mat = vec.transform("Python Developer with Flask, SQL, and Docker")
        self.assertGreater(vec.vocab_size, 0)
        self.assertEqual(mat.shape[0], 1)

    def test_gap13_spacy_ner_extracts_skills_without_crash(self):
        """spaCy NER model extracts canonical skills reliably."""
        from app.ml.skill_extraction.extract_skills import extract_skills, is_ner_available
        self.assertTrue(is_ner_available())

        sample_text = "Proficient in Python, Machine Learning, Docker, and PostgreSQL."
        skills = extract_skills(sample_text)
        self.assertIsInstance(skills, list)
        self.assertTrue(any(s.lower() == "python" for s in skills))

    # ============================================================
    # GAP-14: OCR Fallback for Scanned PDFs
    # ============================================================

    def test_gap14_is_insufficient_text_evaluator(self):
        """is_insufficient_text accurately flags empty, short, and meaningless strings."""
        self.assertTrue(is_insufficient_text(""))
        self.assertTrue(is_insufficient_text("   \n\t  "))
        self.assertTrue(is_insufficient_text("Short"))
        self.assertTrue(is_insufficient_text("123 456 789 000 !!! ???"))
        self.assertFalse(is_insufficient_text(
            "Experienced Python Developer with 5 years building web applications and AI models in Django and Flask."
        ))

    def test_gap14_normal_text_pdf_does_not_trigger_ocr(self):
        """Standard text PDF extracts text using PyPDF2 directly without invoking OCR."""
        text_content = (
            "Alex Morgan\n"
            "Software Engineer - Python Developer\n"
            "Skills: Python, Flask, SQL, Docker\n"
            "Experience: 3 years developing REST APIs at TechCorp\n"
            "Education: Bachelor of Science in Computer Science"
        )
        pdf_stream = _create_synthetic_text_pdf(text_content)
        result = extract_pdf_with_metadata(pdf_stream, filename="normal_resume.pdf")

        self.assertTrue(result["success"])
        self.assertEqual(result["metadata"]["parser_name"], "PyPDF2")
        self.assertFalse(result["metadata"]["ocr_applied"])
        self.assertIn("Python", result["raw_text"])

    def test_gap14_scanned_pdf_triggers_ocr_fallback(self):
        """Scanned image-only PDF triggers OCR fallback and extracts meaningful text."""
        fictional_resume = (
            "Jordan Reed\n"
            "Full Stack Developer\n"
            "Skills: Python, React, PostgreSQL, Docker\n"
            "Education: B.Tech Computer Science\n"
            "Experience: 4 years software development"
        )
        scanned_pdf_stream = _create_synthetic_scanned_pdf(fictional_resume)

        # Set mock OCR handler representing engine transcription
        def mock_engine(images):
            return fictional_resume

        set_mock_ocr_handler(mock_engine)

        result = extract_pdf_with_metadata(scanned_pdf_stream, filename="scanned_resume.pdf")

        self.assertTrue(result["success"])
        self.assertTrue(result["metadata"]["ocr_applied"])
        self.assertIn("OCR Fallback", result["metadata"]["parser_name"])
        self.assertIn("Jordan Reed", result["raw_text"])
        self.assertIn("Python", result["raw_text"])

    def test_gap14_scanned_pdf_flows_into_resume_intelligence(self):
        """OCR-extracted text from scanned PDF successfully builds complete Resume Intelligence JSON."""
        fictional_resume = (
            "Morgan Blake\n"
            "Email: morgan.blake@example.com\n"
            "Phone: 9876543210\n"
            "Skills: Python, Flask, Machine Learning, SQL\n"
            "Education: Master of Technology · IIT Bombay\n"
            "Experience:\n"
            "Lead AI Engineer at InnovateTech (2020 - Present)\n"
            "Developed scalable recruitment AI and NLP parsers."
        )
        scanned_pdf_stream = _create_synthetic_scanned_pdf(fictional_resume)

        set_mock_ocr_handler(lambda images: fictional_resume)

        intel = build_resume_intelligence(scanned_pdf_stream, filename="scanned_alex.pdf")

        self.assertEqual(intel["metadata"]["parse_status"].lower(), "success")
        self.assertTrue(intel["metadata"].get("ocr_applied"))
        self.assertIn("Python", [s["name"] for s in intel["skills"]])
        self.assertEqual(intel["contact"]["email"], "morgan.blake@example.com")
        self.assertGreater(intel["quality"]["quality_score"], 0)

    def test_gap14_ocr_unavailable_graceful_failure(self):
        """When OCR engine is unavailable, system returns graceful failure without crashing."""
        scanned_pdf_stream = _create_synthetic_scanned_pdf("Any Content")

        with patch("app.services.ocr_service.is_ocr_engine_available", return_value=(False, "Tesseract not installed")):
            clear_mock_ocr_handler()
            result = extract_pdf_with_metadata(scanned_pdf_stream, filename="scanned_no_engine.pdf")

            self.assertFalse(result["success"])
            self.assertIn("OCR engine is", result["errors"][0])

    def test_gap14_docx_parsing_remains_unaffected(self):
        """Normal DOCX documents continue to parse via python-docx without invoking OCR."""
        from app.ml.parsers.docx_parser import extract_docx_with_metadata
        docx_path = os.path.join(_APP_ROOT, "datasets", "sample_resumes", "Jorgen_CV.docx")
        if os.path.exists(docx_path):
            with open(docx_path, "rb") as f:
                res = extract_docx_with_metadata(f, "Jorgen_CV.docx")
            self.assertTrue(res["success"])
            self.assertEqual(res["metadata"]["file_type"], "docx")


if __name__ == "__main__":
    unittest.main()
