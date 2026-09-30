# HireAI / TalentSync — Test Suite Baseline

**Generated**: 2026-09-02  
**Phase**: Phase 0 — Baseline & System Freeze  
**Mode**: Read-Only Audit  

---

## 1. Test Suite Execution Verification

The complete automated test suite was executed in read-only verification mode on 2026-09-02:

```text
Command:
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
Working Directory:
V:\HireAI_Website-main (2)\AI-Resume-Screening-System
```

### Execution Results:
- **Total Tests Run**: **201 tests**
- **Passed**: **201 tests**
- **Failed**: **0**
- **Errors**: **0**
- **Skipped**: **0**
- **Pass Rate**: **100.0%**
- **Execution Time**: **20.507 seconds**

---

## 2. Test File Inventory & Granular Breakdown

| Test File | Module Under Test | Test Focus / Scope | Status |
| :--- | :--- | :--- | :---: |
| `test_auth_p0.py` | `auth_controller.py`, `auth_routes.py` | 10-char password policy, lockout (5 attempts), token expiry, constant-time compare | ✅ 14/14 PASS |
| `test_resume_upload_p0.py` | `resume_controller.py`, `validators.py`| Magic-byte validation, disk storage, SHA-256 duplicate detection, rate limiting | ✅ PASS |
| `test_resume_intelligence_foundation_p0.py` | `section_detector.py` | Header fuzzy matching, bounding lines, confidence scores | ✅ PASS |
| `test_entity_extractor.py` | `entity_extractor.py` | Name NER, email regex, phone normalization, LinkedIn/GitHub URLs | ✅ PASS |
| `test_skill_intelligence.py` | `skill_intelligence.py` | Canonical taxonomy matching, category assignment, proficiency detection | ✅ PASS |
| `test_experience_extractor.py` | `experience_extractor.py` | Work timeline, role/company extraction, total years calculation | ✅ PASS |
| `test_education_extractor.py` | `education_extractor.py` | Degree normalization (B.Tech/M.S.), university extraction, GPA detection | ✅ PASS |
| `test_resume_quality_analyzer.py`| `resume_quality_analyzer.py`| 5-factor quality score, action verbs, quantified metrics | ✅ PASS |
| `test_resume_intelligence_builder.py`| `resume_json_builder.py` | Canonical JSON construction, schema validation | ✅ PASS |
| `test_ri_integration_05_persistence.py`| Integration / Persistence | Transactional DB insertion of structured_json and user profile sync | ✅ PASS |
| `test_recommendation.py` | `recommend_jobs.py` | TF-IDF Cosine Similarity and skill overlap ranking | ✅ PASS |
| `test_resume_parser.py` | `pdf_parser.py`, `docx_parser.py` | PDF & DOCX in-memory text parsing | ✅ PASS |

---

## 3. Test Environment Isolation Observation

- **Finding**: Several tests initialize Flask via `create_app()`, which binds to `ActiveConfig.DB_FILE` (`talentsync.db`).
- **Observation**: During tests, temporary test user accounts (e.g. `ri05_cand_...`, `lockout_...`) and test resume rows are inserted into the database.
- **Safety Action Taken in Phase 0**: Prior to running tests, an exact verified backup of the database was saved to `docs/baseline/backups/talentsync_baseline_20260902_182512.db` with identical SHA-256 hash.
