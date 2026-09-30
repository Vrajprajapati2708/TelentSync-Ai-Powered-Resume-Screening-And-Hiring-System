# HireAI / TalentSync — Resume Intelligence (RI) Baseline

**Generated**: 2026-09-02  
**Phase**: Phase 0 — Baseline & System Freeze  
**Mode**: Read-Only Audit  

---

## 1. Resume Intelligence Architecture Pipeline

The Resume Intelligence engine represents the core AI/NLP parsing pipeline implemented on Aug 11, 2026:

```text
[ Binary Resume File (PDF / DOCX) ]
             │
             ▼
[ Validation: Magic-Bytes & SHA-256 Hash ]
             │
             ▼
[ Document Parsers: pdf_parser.py / docx_parser.py ]
             │ (Raw text extraction)
             ▼
[ Section Detector: section_detector.py ]
   ├── Summary, Skills, Experience, Education, Projects, Certifications
   └── Section bounding line indices & confidence scores
             │
             ├──► [ Entity Extractor: entity_extractor.py ]
             │       └── Name, Email, Phone, LinkedIn, GitHub, Portfolio
             │
             ├──► [ Skill Intelligence: skill_intelligence.py ]
             │       └── Canonical tech skills mapped to categories & taxonomy
             │
             ├──► [ Experience Extractor: experience_extractor.py ]
             │       └── Job titles, companies, dates, durations, total years
             │
             ├──► [ Education Extractor: education_extractor.py ]
             │       └── Degrees, universities, graduation years, GPA/CGPA
             │
             └──► [ Resume Quality Analyzer: resume_quality_analyzer.py ]
                     └── 5-factor quality metrics (0-100 score, completeness, format, verbs, metrics)
             │
             ▼
[ Canonical JSON Builder: resume_json_builder.py ]
   └── Serializes uniform structured_json payload
             │
             ▼
[ Database Persistence: SQLite resumes.structured_json ]
   └── SAVED (Verified by test_ri_integration_05_persistence.py)
             │
             X  <-- BROKEN / DISCONNECTED LINK
             ▼
[ API Response: resume_controller.py:236 ]
   └── OMITTED: controller returns only flat legacy fields (skills, ats_score)
             │
             X  <-- BROKEN / DISCONNECTED LINK
             ▼
[ Frontend SPA Consumption: app.js & index.html ]
   └── NOT RENDERED: No UI elements display parsed experience, education, or quality breakdown
```

---

## 2. Component Inventory & Status

| Module File | Class / Functions | Status | Verification Evidence |
| :--- | :--- | :---: | :--- |
| `app/ml/parsers/section_detector.py` | `detect_sections()`, `split_by_sections()` | ✅ Verified | Tested via `test_resume_intelligence_foundation_p0.py` |
| `app/ml/parsers/entity_extractor.py` | `extract_contact_info()`, `extract_name()` | ✅ Verified | Tested via `test_entity_extractor.py` |
| `app/ml/skill_extraction/skill_intelligence.py` | `extract_skills_intelligence()` | ✅ Verified | Tested via `test_skill_intelligence.py` |
| `app/ml/parsers/experience_extractor.py` | `extract_experience()` | ✅ Verified | Tested via `test_experience_extractor.py` |
| `app/ml/parsers/education_extractor.py` | `extract_education()` | ✅ Verified | Tested via `test_education_extractor.py` |
| `app/ml/analyzers/resume_quality_analyzer.py` | `analyze_resume_quality()` | ✅ Verified | Tested via `test_resume_quality_analyzer.py` |
| `app/ml/resume_intelligence/resume_json_builder.py`| `build_resume_intelligence()` | ✅ Verified | Tested via `test_resume_intelligence_builder.py` |
| `app/controllers/resume_controller.py` | `process_resume_upload()` | ⚠️ Partial | Saves to DB, but omits intelligence from JSON response |
| `app/static/js/app.js` | UI rendering | ❌ Disconnected | Does not parse or render `intel` or `structured_json` |

---

## 3. Disconnect Analysis

1. **Backend Serialization Disconnect**:
   `resume_controller.py` calls `build_resume_intelligence()`, gets `intel`, serializes it to `structured_json_str`, and writes it to SQLite. However, line 236 creates the HTTP return payload omitting `intel`!
2. **Frontend UI Disconnect**:
   `app.js` never receives the experience timeline, education degrees, or quality breakdown, and `index.html` has no markup to render these fields.
