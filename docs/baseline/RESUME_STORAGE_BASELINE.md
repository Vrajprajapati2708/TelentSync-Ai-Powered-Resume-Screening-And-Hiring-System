# HireAI / TalentSync — Resume Storage Baseline

**Generated**: 2026-09-02  
**Phase**: Phase 0 — Baseline & System Freeze  
**Mode**: Read-Only Audit  

---

## 1. Storage Location & Directory Inventory

| Parameter | Observed Value |
| :--- | :--- |
| **Active Storage Path** | `V:\HireAI_Website-main (2)\AI-Resume-Screening-System\uploads\resumes` |
| **Alternative/Config Path** | `V:\HireAI_Website-main (2)\AI-Resume-Screening-System\app\static\uploads` (0 files) |
| **Outer Path** | `V:\HireAI_Website-main (2)\uploads` (Does not exist) |
| **Total Uploaded Files** | **172 files** |
| **File Formats / Extensions** | **172 `.docx` files** (100% Word Document XML format) |
| **Total Disk Storage Size** | **6,073,398 bytes (~5.79 MB)** |
| **Average File Size** | ~35.3 KB per resume document |

---

## 2. Naming Convention & Security Pattern

- **Filename Pattern**: `res_<user_id>_<12_hex_uuid>.<ext>`
- **Sample Files**:
  - `res_1009_8eae6f5fcc27.docx`
  - `res_1013_150c9794a2ef.docx`
  - `res_1016_614d4fe9ad64.docx`
  - `res_1019_d2c2590d9b57.docx`
- **Security Validation**:
  - Filenames use sanitized UUID hashes to avoid directory traversal attacks.
  - Original candidate filenames (e.g. `Jorgen_CV.docx`, `Test_Resume_Python.docx`) are stored safely in SQLite `resumes.original_name` and never used directly as disk paths.

---

## 3. Database Linkage & Referential Integrity

- **Database `resumes` table rows**: **192 rows**.
- **Files physically present on disk**: **172 files**.
- **Discrepancy (20 records)**: 20 records represent unit/mock tests (e.g. `test_resume_upload_p0.py` and `test_ri_integration_05_persistence.py`) where files were written to temporary mock fixtures or cleaned up during teardown.
- **Physical Document Integrity**: All 172 disk files match valid user IDs and have non-null file hashes in SQLite.
