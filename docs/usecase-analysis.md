# HireAI (TalentSync) — Use Case Analysis Specification

**Document Version**: 2.0.0  
**Standard**: UML 2.5 Use Case Metamodel  
**System Boundary**: HireAI (TalentSync) AI-Powered Recruitment Platform  

---

## 1. Actors Specification

### 1.1 Primary Human Actors
| Actor ID | Actor Name | Role & Responsibility |
| :--- | :--- | :--- |
| `ACT_CAND` | **Candidate** | Job seeker / student applying for positions, uploading resumes, tracking ATS scores. |
| `ACT_HR` | **HR Recruiter** | Hiring manager posting job openings, reviewing AI-ranked candidates, updating hiring status. |
| `ACT_ADM` | **Platform Admin** | System administrator managing user accounts, auditing ML outliers, inspecting logs and API health. |

### 1.2 Secondary External System Actors
| Actor ID | System Name | Nature of Integration |
| :--- | :--- | :--- |
| `EXT_EMAIL` | **Email Service (SMTP)** | Delivers verification OTPs, password reset links, and application status notifications. |
| `EXT_ADZUNA`| **Adzuna Job API** | Third-party REST service providing external live job vacancy listings and provider health status. |

---

## 2. Complete Use Case Catalog (28 Use Cases)

### Zone 1: Shared Authentication Flow (`Zone_Auth`)
| UC ID | Use Case Name | Primary Actor(s) | Relationships | Description |
| :--- | :--- | :--- | :--- | :--- |
| `UC1` | **Register Account** | Candidate, HR | `<<include>> UC1.1` | Creates new user credentials in the system. |
| `UC1.1`| **Verify Email (OTP)** | System (Internal) | Included by `UC1` ➔ `EXT_EMAIL` | Verifies candidate/HR email address via token/OTP dispatch. |
| `UC2` | **Login** | Candidate, HR, Admin | Extended by `UC2.1` | Authenticates user via role-based credentials and issues session. |
| `UC2.1`| **Reset Password** | Candidate, HR, Admin | `<<extend>> UC2` [on forgotten password] | Allows user to reset lost credentials via verified email token. |

### Zone 2: Candidate Journey (`Zone_Cand`)
| UC ID | Use Case Name | Primary Actor(s) | Relationships | Description |
| :--- | :--- | :--- | :--- | :--- |
| `UC3` | **Upload Resume** | Candidate | `<<include>> UC3.1` | Uploads PDF or DOCX resume document. |
| `UC3.1`| **Parse Resume & Extract Skills** | System (NLP) | Included by `UC3`, `<<include>> UC3.2` | Extracts raw text, entities, skills, and experience via spaCy NER. |
| `UC3.2`| **Compute ATS Score** | System (AI) | Included by `UC3.1`, Extended by `UC3.3` | Computes standardized 0–100 ATS compatibility metric. |
| `UC3.3`| **Flag Keyword-Stuffing Outlier**| System (ML) | `<<extend>> UC3.2` [score > 95% / anomaly] | Flags abnormal score inflation using Isolation Forest model. |
| `UC4` | **View Candidate Dashboard** | Candidate | `<<include>> UC4.1`, Extended by `UC4.2` | Primary candidate dashboard displaying application stats and matches. |
| `UC4.1`| **View Skill Gap Feedback** | Candidate | Included by `UC4` | Displays matched skills vs missing skills gap analysis. |
| `UC4.2`| **Download ATS Report (PDF)** | Candidate | `<<extend>> UC4` [on user request] | Generates and exports downloadable ATS evaluation report in PDF. |
| `UC5` | **Discover Job Matches** | Candidate | Extended by `UC5.1` | Displays AI-matched internal job postings. |
| `UC5.1`| **Search Live External Jobs** | Candidate | `<<extend>> UC5` [toggle external] ➔ `EXT_ADZUNA` | Queries Adzuna API for live external job vacancies. |
| `UC6` | **Apply for Job** | Candidate | `<<include>> UC6.1` | Submits candidate profile and resume to a specific job vacancy. |
| `UC6.1`| **Calculate Match Score** | System (AI) | Included by `UC6` | Executes TF-IDF and weighted scoring model against job requirements. |
| `UC7` | **Track Application Status** | Candidate | None | Monitors real-time status progression (*Pending*, *Reviewing*, *Shortlisted*, *Rejected*). |

### Zone 3: HR Recruiter Journey (`Zone_HR`)
| UC ID | Use Case Name | Primary Actor(s) | Relationships | Description |
| :--- | :--- | :--- | :--- | :--- |
| `UC8` | **Post Job Vacancy** | HR Recruiter | `<<include>> UC8.1` | Creates new employment vacancy listing with job specs. |
| `UC8.1`| **Define Required Skills** | HR Recruiter | Included by `UC8` | Specifies essential skills, experience requirements, and job description. |
| `UC9` | **View Ranked Applicants** | HR Recruiter | `<<include>> UC9.1`, Extended by `UC9.2`, `UC9.3` | Displays applicants for posted vacancies sorted by suitability. |
| `UC9.1`| **AI Match Leaderboard** | System (AI) | Included by `UC9` | Ranks all applicants dynamically using computed match percentages. |
| `UC9.2`| **Inspect Outlier Profiles** | HR Recruiter | `<<extend>> UC9` [if outlier flagged] | Reviews profiles tagged by Isolation Forest for suspicious keywords. |
| `UC9.3`| **Filter by Clusters (K-Means)** | HR Recruiter | `<<extend>> UC9` [optional filter] | Groups applicants into unsupervised candidate clusters. |
| `UC10` | **Update Application Status** | HR Recruiter | `<<include>> UC10.1` | Transitions candidate state to *Shortlisted* or *Rejected*. |
| `UC10.1`| **Send Status Notification** | System (Email)| Included by `UC10` ➔ `EXT_EMAIL` | Automatically dispatches status notification email to candidate. |
| `UC11` | **View Hiring Analytics** | HR Recruiter | None | Provides hiring funnel charts, application counts, and match rates. |

### Zone 4: Platform Admin Journey (`Zone_Admin`)
| UC ID | Use Case Name | Primary Actor(s) | Relationships | Description |
| :--- | :--- | :--- | :--- | :--- |
| `UC12` | **Manage User Accounts** | Platform Admin | Extended by `UC12.1` | Views, audits, and manages candidate and recruiter accounts. |
| `UC12.1`| **Deactivate / Ban Malicious User**| Platform Admin | `<<extend>> UC12` [on rule violation] | Suspends malicious accounts or abusers. |
| `UC13` | **Audit Security & ML Outliers**| Platform Admin | `<<include>> UC13.1`, `<<include>> UC13.2` | Oversees platform-wide fraud guard and authentication security. |
| `UC13.1`| **Inspect IsolationForest Flags**| Platform Admin | Included by `UC13` | Directly audits statistical outlier anomalies across all resumes. |
| `UC13.2`| **Monitor Failed Logins** | Platform Admin | Included by `UC13` | Inspects brute-force login attempt logs. |
| `UC14` | **Monitor Platform Health** | Platform Admin | `<<include>> UC14.1` | Inspects system services, database status, and API availability. |
| `UC14.1`| **Check External API Health** | System (Admin)| Included by `UC14` ➔ `EXT_ADZUNA` | Pings Adzuna API provider health and cache status. |
| `UC15` | **View System Audit Logs** | Platform Admin | None | Reads immutable system audit trail records. |

---

## 3. Structural Rules & UML Compliance Matrix
1. **Flow Ordering:** Top-to-bottom layout across 4 sequential operational zones.
2. **Include Compliance:** All included use cases represent strictly required base sub-behaviors.
3. **Extend Compliance:** All extending use cases define explicit extension points with bracketed triggers.
4. **Boundary Isolation:** Only Primary Actors connect from outside the boundary via solid associations to Column 1 Base Use Cases.
