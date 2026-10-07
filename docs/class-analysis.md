# HireAI (TalentSync) — System Class Diagram Specification

**Document Version**: 2.0.0  
**Standard**: UML 2.5 Class Diagram Specification  
**Scope**: Core Domain Entities, Attributes, Methods, and Multiplicity  
**Artifacts Generated**:
* Native Draw.io file: [`docs/class-diagram.drawio`](file:///v:/HireAI_Website-main%20(2)/docs/class-diagram.drawio)
* PlantUML source code: [`docs/class-diagram.puml`](file:///v:/HireAI_Website-main%20(2)/docs/class-diagram.puml)

---

## 1. Domain Enumerations

| Enumeration Name | Allowed Values | Semantic Meaning |
| :--- | :--- | :--- |
| **`UserRole`** | `candidate`, `hr`, `admin` | User authorization role and permission boundary |
| **`ApplicationStatus`**| `Reviewing`, `Shortlisted`, `Pending`, `Rejected` | Application lifecycle progression states |
| **`JobStatus`** | `Active`, `Closed`, `Draft` | Job vacancy visibility and recruitment state |

---

## 2. Core 8 Domain Entities (Main System Classes)

### 1. `User` (Identity, Authentication & Candidate Profile)
* **Description:** Represents all human users across the platform (Candidates, HR Recruiters, and Admins) with role-based attributes.
* **Attributes:**
  * `+ id : int <<PK>>`
  * `+ name : string`
  * `+ email : string`
  * `+ password : string` (Cryptographic hash)
  * `+ role : UserRole`
  * `+ is_verified : int` (0 = unverified, 1 = verified)
  * `+ skills : string` (Comma-separated parsed skills)
  * `+ ats_score : int` (Overall ATS score 0–100)
  * `+ is_outlier : int` (0 = normal, 1 = flagged suspicious by IsolationForest)
  * `+ cluster_label : string` (K-Means candidate skill cluster)
  * `+ created_at : DateTime`
* **Methods:**
  * `+ is_candidate() : bool`
  * `+ is_hr() : bool`
  * `+ is_admin() : bool`

### 2. `Resume` (Document & NLP ATS Intelligence)
* **Description:** Represents uploaded candidate resumes, parsed text content, and extracted semantic entities.
* **Attributes:**
  * `+ id : int <<PK>>`
  * `+ user_id : int <<FK>>`
  * `+ original_name : string`
  * `+ file_path : string`
  * `+ file_hash : string` (SHA-256 integrity hash)
  * `+ ats_score : int` (0–100 score)
  * `+ extracted_skills : string`
  * `+ structured_json : string` (Parsed profile JSON)
  * `+ uploaded_at : DateTime`
* **Methods:**
  * `+ has_structured_json() : bool`

### 3. `Job` (Internal Job Vacancy)
* **Description:** Represents employer-created job openings posted directly by HR recruiters.
* **Attributes:**
  * `+ id : int <<PK>>`
  * `+ hr_id : int <<FK>>`
  * `+ title : string`
  * `+ company : string`
  * `+ location : string`
  * `+ skills : string`
  * `+ description : string`
  * `+ status : JobStatus`
  * `+ created_at : DateTime`
* **Methods:**
  * `+ is_active() : bool`

### 4. `ExternalJob` (Live Vacancies via Adzuna API)
* **Description:** Represents aggregated live employment vacancies fetched from external provider APIs.
* **Attributes:**
  * `+ id : int <<PK>>`
  * `+ external_id : string`
  * `+ provider : string`
  * `+ title : string`
  * `+ company : string`
  * `+ location : string`
  * `+ skills : string`
  * `+ apply_url : string`
  * `+ status : JobStatus`
* **Methods:**
  * `+ is_remote() : bool`

### 5. `Application` (Central Transaction Join)
* **Description:** Central candidate-to-job application junction entity linking applicant, vacancy, and match score.
* **Attributes:**
  * `+ id : int <<PK>>`
  * `+ user_id : int <<FK>>`
  * `+ job_id : int <<FK>>`
  * `+ match_score : int` (AI-calculated match percentage)
  * `+ status : ApplicationStatus`
  * `+ applied_at : DateTime`
* **Methods:**
  * `+ is_shortlisted() : bool`
  * `+ can_transition(new_status : ApplicationStatus) : bool`

### 6. `ApplicationStatusHistory` (Audit Trail)
* **Description:** Immutable transition log tracking every hiring state change (*Pending* ➔ *Reviewing* ➔ *Shortlisted*/*Rejected*).
* **Attributes:**
  * `+ id : int <<PK>>`
  * `+ application_id : int <<FK>>`
  * `+ status : ApplicationStatus`
  * `+ notes : string`
  * `+ updated_at : DateTime`
* **Methods:**
  * `+ record_transition()`

### 7. `SavedJob` (Candidate Bookmarks)
* **Description:** Bookmarked vacancies saved by candidates, supporting dual polymorphic foreign keys (internal or external).
* **Attributes:**
  * `+ id : int <<PK>>`
  * `+ user_id : int <<FK>>`
  * `+ job_id : int <<FK, nullable>>`
  * `+ external_id : string <<nullable>>`
  * `+ saved_at : DateTime`
* **Methods:**
  * `+ is_external() : bool`

### 8. `RecommendationHistory` (AI Match Snapshots)
* **Description:** Historical snapshot records of AI recommendations provided to candidates with skill-gap feedback.
* **Attributes:**
  * `+ id : int <<PK>>`
  * `+ user_id : int <<FK>>`
  * `+ job_id : int <<FK, nullable>>`
  * `+ external_id : string <<nullable>>`
  * `+ match_score : int`
  * `+ matched_skills : string`
  * `+ missing_skills : string`
  * `+ recommended_at : DateTime`
* **Methods:**
  * `+ get_match_summary()`

---

## 3. Relationships & Multiplicity Matrix

| Source Class | Multiplicity | Relationship Type | Target Class | Multiplicity | UML Verb / Meaning |
| :--- | :---: | :--- | :--- | :---: | :--- |
| **`User`** | `1` | Composition (`*--`) | **`Resume`** | `0..*` | User owns multiple uploaded resumes |
| **`User`** | `1` | Association (`--`) | **`Job`** | `0..*` | HR User posts multiple job vacancies |
| **`User`** | `1` | Association (`--`) | **`Application`** | `0..*` | Candidate User submits multiple applications |
| **`Job`** | `1` | Association (`--`) | **`Application`** | `0..*` | Job receives multiple candidate applications |
| **`Application`** | `1` | Composition (`*--`) | **`ApplicationStatusHistory`** | `1..*` | Application owns its audit history transitions |
| **`User`** | `1` | Association (`--`) | **`SavedJob`** | `0..*` | Candidate bookmarks multiple jobs |
| **`User`** | `1` | Association (`--`) | **`RecommendationHistory`** | `0..*` | Candidate receives AI recommendations |
| **`SavedJob`** | `0..*` | Dependency (`..>`) | **`Job`** | `0..1` | Optional reference to internal job |
| **`SavedJob`** | `0..*` | Dependency (`..>`) | **`ExternalJob`** | `0..1` | Optional reference to live external job |
| **`RecommendationHistory`** | `0..*` | Dependency (`..>`) | **`Job`** | `0..1` | Optional reference to internal job |
| **`RecommendationHistory`** | `0..*` | Dependency (`..>`) | **`ExternalJob`** | `0..1` | Optional reference to live external job |
