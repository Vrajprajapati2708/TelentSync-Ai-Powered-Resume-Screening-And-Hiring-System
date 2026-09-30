# ============================================================
#  TalentSync — Synthetic Resume & Job Dataset Generator
#
#  Generates realistic synthetic training data with:
#    - 600 candidate resume texts (varied roles, experience)
#    - 200 job descriptions (varied requirements)
#    - Skill annotations for spaCy NER training
#
#  This data trains the TF-IDF recommender and the NER model.
#  Run standalone:  python -m app.ml.training.generate_dataset
# ============================================================

import random
import json
import os
from pathlib import Path

# ── Seed for reproducibility ─────────────────────────────────
random.seed(42)

# ── Base Skills by Domain ────────────────────────────────────
SKILL_POOL = {
    "python":            "Programming Languages",
    "java":              "Programming Languages",
    "javascript":        "Programming Languages",
    "typescript":        "Programming Languages",
    "c++":               "Programming Languages",
    "c#":                "Programming Languages",
    "go":                "Programming Languages",
    "rust":              "Programming Languages",
    "scala":             "Programming Languages",
    "kotlin":            "Programming Languages",
    "r":                 "Programming Languages",
    "swift":             "Programming Languages",
    "bash":              "Programming Languages",
    "sql":               "Databases",
    "mysql":             "Databases",
    "postgresql":        "Databases",
    "mongodb":           "Databases",
    "redis":             "Databases",
    "elasticsearch":     "Databases",
    "sqlite":            "Databases",
    "cassandra":         "Databases",
    "dynamodb":          "Databases",
    "firebase":          "Databases",
    "react":             "Web Frameworks",
    "angular":           "Web Frameworks",
    "vue.js":            "Web Frameworks",
    "node.js":           "Web Frameworks",
    "flask":             "Web Frameworks",
    "django":            "Web Frameworks",
    "fastapi":           "Web Frameworks",
    "express":           "Web Frameworks",
    "spring":            "Web Frameworks",
    "html":              "Web Frameworks",
    "css":               "Web Frameworks",
    "bootstrap":         "Web Frameworks",
    "tailwind":          "Web Frameworks",
    "machine learning":  "Data Science",
    "deep learning":     "Data Science",
    "nlp":               "Data Science",
    "computer vision":   "Data Science",
    "data science":      "Data Science",
    "statistics":        "Data Science",
    "data analysis":     "Data Science",
    "feature engineering": "Data Science",
    "time series":       "Data Science",
    "reinforcement learning": "Data Science",
    "pandas":            "ML Libraries",
    "numpy":             "ML Libraries",
    "scikit-learn":      "ML Libraries",
    "tensorflow":        "ML Libraries",
    "pytorch":           "ML Libraries",
    "keras":             "ML Libraries",
    "xgboost":           "ML Libraries",
    "lightgbm":          "ML Libraries",
    "opencv":            "ML Libraries",
    "nltk":              "ML Libraries",
    "spacy":             "ML Libraries",
    "hugging face":      "ML Libraries",
    "transformers":      "ML Libraries",
    "langchain":         "ML Libraries",
    "matplotlib":        "ML Libraries",
    "seaborn":           "ML Libraries",
    "plotly":            "ML Libraries",
    "aws":               "Cloud & DevOps",
    "azure":             "Cloud & DevOps",
    "gcp":               "Cloud & DevOps",
    "docker":            "Cloud & DevOps",
    "kubernetes":        "Cloud & DevOps",
    "terraform":         "Cloud & DevOps",
    "jenkins":           "Cloud & DevOps",
    "ci/cd":             "Cloud & DevOps",
    "github actions":    "Cloud & DevOps",
    "linux":             "Cloud & DevOps",
    "git":               "Cloud & DevOps",
    "ansible":           "Cloud & DevOps",
    "tableau":           "BI & Analytics",
    "power bi":          "BI & Analytics",
    "excel":             "BI & Analytics",
    "hadoop":            "BI & Analytics",
    "spark":             "BI & Analytics",
    "kafka":             "BI & Analytics",
    "mlflow":            "ML Ops",
    "airflow":           "ML Ops",
    "dbt":               "ML Ops",
    "grafana":           "ML Ops",
    "prometheus":        "ML Ops",
}

ALL_SKILLS = list(SKILL_POOL.keys())

# ── Job Role Profiles ────────────────────────────────────────
JOB_PROFILES = {
    "Data Scientist": {
        "core": ["python", "machine learning", "pandas", "numpy", "scikit-learn",
                 "statistics", "data science", "matplotlib", "sql"],
        "nice": ["tensorflow", "pytorch", "deep learning", "feature engineering",
                 "r", "tableau", "xgboost", "spark"]
    },
    "ML Engineer": {
        "core": ["python", "tensorflow", "pytorch", "deep learning", "docker",
                 "mlflow", "scikit-learn", "aws", "kubernetes"],
        "nice": ["airflow", "kubernetes", "git", "ci/cd", "fastapi", "cuda", "spark"]
    },
    "NLP Engineer": {
        "core": ["python", "nlp", "spacy", "transformers", "hugging face",
                 "pytorch", "nltk", "langchain"],
        "nice": ["tensorflow", "bert", "gpt", "elasticsearch", "fastapi", "docker"]
    },
    "Data Analyst": {
        "core": ["sql", "excel", "tableau", "power bi", "statistics", "python",
                 "data analysis"],
        "nice": ["r", "pandas", "matplotlib", "seaborn", "plotly", "hadoop", "spark"]
    },
    "Data Engineer": {
        "core": ["python", "sql", "spark", "hadoop", "kafka", "aws", "docker",
                 "airflow", "postgresql"],
        "nice": ["dbt", "kubernetes", "terraform", "git", "mongodb", "redis"]
    },
    "Python Developer": {
        "core": ["python", "django", "flask", "fastapi", "postgresql", "git",
                 "docker", "sql", "redis"],
        "nice": ["aws", "celery", "javascript", "html", "css", "mongodb"]
    },
    "Full Stack Developer": {
        "core": ["javascript", "typescript", "react", "node.js", "html", "css",
                 "sql", "git", "mongodb"],
        "nice": ["python", "docker", "aws", "postgresql", "redis", "tailwind", "express"]
    },
    "Cloud Architect": {
        "core": ["aws", "azure", "kubernetes", "terraform", "docker", "linux",
                 "ci/cd", "git"],
        "nice": ["python", "ansible", "jenkins", "gcp", "prometheus", "grafana"]
    },
    "DevOps Engineer": {
        "core": ["linux", "docker", "kubernetes", "ci/cd", "git", "aws",
                 "ansible", "terraform"],
        "nice": ["python", "bash", "jenkins", "github actions", "prometheus", "grafana"]
    },
    "Computer Vision Engineer": {
        "core": ["python", "opencv", "pytorch", "tensorflow", "deep learning",
                 "computer vision", "numpy"],
        "nice": ["cuda", "docker", "scikit-learn", "matplotlib", "aws"]
    },
}

# ── Sentence Templates ────────────────────────────────────────
EXPERIENCE_TEMPLATES = [
    "Developed and deployed {skill1} applications at scale using {skill2}.",
    "Built {skill1}-based microservices leveraging {skill2} for high availability.",
    "Implemented {skill1} pipelines to process and analyse large datasets using {skill2}.",
    "Designed and maintained {skill1} infrastructure on {skill2} cloud platform.",
    "Led development of {skill1} models achieving 92% accuracy using {skill2}.",
    "Collaborated in an agile team to deliver {skill1} solutions with {skill2}.",
    "Optimized {skill1} performance by 40% through {skill2} integration.",
    "Created automated {skill1} workflows and CI/CD pipelines using {skill2}.",
    "Engineered real-time data streaming pipelines with {skill1} and {skill2}.",
    "Mentored junior developers on {skill1} best practices and {skill2} usage.",
    "Architected end-to-end {skill1} system integrating {skill2} for data storage.",
    "Deployed {skill1} models as REST APIs using {skill2} with 99.9% uptime.",
    "Performed exploratory data analysis using {skill1}, generating insights with {skill2}.",
    "Trained and fine-tuned {skill1} models on domain-specific datasets via {skill2}.",
    "Automated infrastructure provisioning for {skill1} environments using {skill2}.",
]

EDUCATION_TEMPLATES = [
    "B.Tech in Computer Science, {university}, {year} (CGPA: {gpa})",
    "M.Tech in Data Science, {university}, {year} (CGPA: {gpa})",
    "B.Sc in Information Technology, {university}, {year} (CGPA: {gpa})",
    "MCA (Master of Computer Applications), {university}, {year} (CGPA: {gpa})",
    "B.E in Electronics & Computer Engineering, {university}, {year} (CGPA: {gpa})",
    "M.Sc in Artificial Intelligence, {university}, {year} (CGPA: {gpa})",
    "BCA (Bachelor of Computer Applications), {university}, {year} (CGPA: {gpa})",
    "Ph.D in Machine Learning, {university}, {year}",
]

UNIVERSITIES = [
    "IIT Bombay", "IIT Delhi", "IIT Madras", "NIT Trichy", "BITS Pilani",
    "VIT Vellore", "Anna University", "Pune University", "Mumbai University",
    "Gujarat Technological University", "Ahmedabad University",
    "Delhi Technological University", "IIIT Hyderabad", "Manipal University",
    "Symbiosis International University", "Amity University",
]

COMPANIES = [
    "Infosys", "TCS", "Wipro", "HCL Technologies", "Tech Mahindra",
    "Google", "Microsoft", "Amazon", "Flipkart", "Swiggy", "Zomato",
    "Paytm", "BYJU'S", "Razorpay", "Freshworks", "Zoho", "Ola",
    "PhonePe", "Dream11", "ShareChat", "Meesho", "Unacademy",
]

CANDIDATE_NAMES = [
    "Rahul Sharma", "Priya Patel", "Amit Kumar", "Sneha Gupta", "Rohan Mehta",
    "Kavya Nair", "Arjun Singh", "Deepika Reddy", "Vikram Joshi", "Ananya Das",
    "Siddharth Verma", "Pooja Agarwal", "Manish Tiwari", "Riya Kapoor",
    "Karan Malhotra", "Shruti Rao", "Nikhil Pandey", "Divya Krishnan",
    "Aakash Shah", "Meera Iyer", "Yash Bhatia", "Nisha Choudhary",
    "Abhishek Mishra", "Tanya Sinha", "Harsh Trivedi", "Sunita Pillai",
]

JOB_DESCRIPTION_PREFIXES = [
    "We are looking for a talented {role} to join our growing team.",
    "Exciting opportunity for an experienced {role} at a fast-growing startup.",
    "Join our world-class engineering team as a {role}.",
    "We are hiring a skilled {role} to help build the next generation of our platform.",
    "Looking for a passionate {role} with strong problem-solving skills.",
]

JOB_DESCRIPTION_REQUIREMENTS = [
    "You will design, build and maintain high-performance systems.",
    "You will collaborate closely with cross-functional teams.",
    "You will own the full development lifecycle from design to deployment.",
    "You will mentor junior engineers and participate in code reviews.",
    "You will work in an agile environment with fast release cycles.",
]


def _pick_skills(profile: dict, num: int) -> list:
    """Pick a realistic skill set for a role."""
    core = list(profile["core"])
    nice = list(profile["nice"])
    random.shuffle(nice)
    selected = core + nice[:max(0, num - len(core))]
    return selected[:num]


def _generate_resume_text(role: str, profile: dict, name: str, num_skills: int | None = None) -> tuple:
    """Generate a realistic resume text and return (text, skill_list)."""
    if num_skills is None:
        num_skills = random.randint(6, 14)

    skills = _pick_skills(profile, num_skills)
    # Add some noise / extras
    extra_skills = random.sample([s for s in ALL_SKILLS if s not in skills],
                                  k=random.randint(0, 3))
    skills = list(dict.fromkeys(skills + extra_skills))  # dedup, keep order

    university = random.choice(UNIVERSITIES)
    year = random.randint(2015, 2023)
    gpa = round(random.uniform(7.0, 9.8), 1)
    company1 = random.choice(COMPANIES)
    company2 = random.choice([c for c in COMPANIES if c != company1])
    exp_years = random.randint(1, 7)
    phone = f"+91 {random.randint(7000000000, 9999999999)}"
    email = f"{name.lower().replace(' ', '.')}@gmail.com"
    linkedin = f"linkedin.com/in/{name.lower().replace(' ', '-')}"
    github = f"github.com/{name.lower().split()[0]}{random.randint(10, 99)}"

    # Generate experience lines
    skill_pairs = [(skills[i % len(skills)], skills[(i + 1) % len(skills)])
                   for i in range(4)]
    exp_lines = [
        random.choice(EXPERIENCE_TEMPLATES).format(skill1=s1.title(), skill2=s2.title())
        for s1, s2 in skill_pairs
    ]

    edu_line = random.choice(EDUCATION_TEMPLATES).format(
        university=university, year=year, gpa=gpa
    )

    resume_text = f"""
{name}
{phone} | {email}
{linkedin} | {github}

SUMMARY
Experienced {role} with {exp_years}+ years of hands-on expertise in {', '.join(skills[:4])}.
Passionate about building scalable, production-ready solutions.

SKILLS
{', '.join(skills)}

EXPERIENCE
{company1} | {role} | {year - exp_years} - Present
- {exp_lines[0]}
- {exp_lines[1]}

{company2} | Junior {role} | {year - exp_years - 2} - {year - exp_years}
- {exp_lines[2]}
- {exp_lines[3]}

EDUCATION
{edu_line}

PROJECTS
Built an end-to-end {skills[0].title()} project using {skills[1].title()} and {skills[2].title()}.
Contributed to open-source {skills[0].title()} library on GitHub.
""".strip()

    return resume_text, skills


def _generate_job_description(role: str, profile: dict) -> tuple:
    """Generate a job description and return (text, required_skills)."""
    num_req = random.randint(4, 8)
    required_skills = _pick_skills(profile, num_req)

    prefix = random.choice(JOB_DESCRIPTION_PREFIXES).format(role=role)
    requirement = random.choice(JOB_DESCRIPTION_REQUIREMENTS)
    salary = f"₹{random.randint(8, 45)} LPA"
    exp_required = random.randint(1, 6)

    jd_text = f"""
{role} — {random.choice(COMPANIES)}
Location: Bangalore / Mumbai / Remote  |  Salary: {salary}

ABOUT THE ROLE
{prefix} {requirement}

REQUIRED SKILLS
{', '.join(required_skills)}

RESPONSIBILITIES
- Design and implement scalable {required_skills[0].title()} solutions.
- Build and maintain {required_skills[1].title()} infrastructure.
- Work with cross-functional teams to deliver high-quality products.
- Write clean, well-documented, testable code.
- Participate in architecture discussions and code reviews.

REQUIREMENTS
- {exp_required}+ years of experience with {required_skills[0].title()}.
- Strong proficiency in {', '.join(required_skills[:3])}.
- Experience with {', '.join(required_skills[3:])}.
- Bachelor's or Master's degree in Computer Science or related field.
""".strip()

    return jd_text, required_skills


def generate_ner_annotations(text: str, skills: list) -> list:
    """
    Generate spaCy-format NER annotations for SKILL entities.
    Returns a list of (start, end, label) tuples.
    """
    import re
    annotations = []
    seen_spans = []

    for skill in skills:
        pattern = re.compile(r'\b' + re.escape(skill) + r'\b', re.IGNORECASE)
        for m in pattern.finditer(text):
            start, end = m.start(), m.end()
            # Avoid overlapping spans
            overlap = any(s < end and start < e for s, e in seen_spans)
            if not overlap:
                annotations.append((start, end, "SKILL"))
                seen_spans.append((start, end))

    return annotations


def generate_dataset(num_resumes: int = 600, num_jobs: int = 200,
                     output_dir: str | None = None) -> dict:
    """
    Generate the full synthetic training dataset.

    Args:
        num_resumes: Number of synthetic resume texts to generate.
        num_jobs:    Number of synthetic job descriptions to generate.
        output_dir:  Directory to save the dataset JSON files.

    Returns:
        dict with 'resumes', 'jobs', 'ner_training_data' keys.
    """
    roles = list(JOB_PROFILES.keys())

    print(f"[DataGen] Generating {num_resumes} resumes and {num_jobs} job descriptions...")

    # ── Generate Resumes ─────────────────────────────────────
    resumes = []
    ner_training_data = []
    for i in range(num_resumes):
        role = random.choice(roles)
        profile = JOB_PROFILES[role]
        name = random.choice(CANDIDATE_NAMES)
        text, skills = _generate_resume_text(role, profile, name)

        annotations = generate_ner_annotations(text, skills)

        resumes.append({
            "id":    i,
            "role":  role,
            "name":  name,
            "text":  text,
            "skills": skills,
        })

        ner_training_data.append({
            "text":        text,
            "entities":    annotations,
        })

    print(f"[DataGen] [OK] Generated {len(resumes)} resumes.")

    # ── Generate Job Descriptions ─────────────────────────────
    jobs = []
    for i in range(num_jobs):
        role = random.choice(roles)
        profile = JOB_PROFILES[role]
        text, required_skills = _generate_job_description(role, profile)
        jobs.append({
            "id":              i,
            "role":            role,
            "text":            text,
            "required_skills": required_skills,
        })

    print(f"[DataGen] [OK] Generated {len(jobs)} job descriptions.")

    dataset = {
        "resumes":           resumes,
        "jobs":              jobs,
        "ner_training_data": ner_training_data,
        "metadata": {
            "num_resumes":    num_resumes,
            "num_jobs":       num_jobs,
            "roles":          roles,
            "total_skills":   len(ALL_SKILLS),
        }
    }

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        resumes_path = Path(output_dir) / "resumes.json"
        jobs_path    = Path(output_dir) / "jobs.json"
        ner_path     = Path(output_dir) / "ner_training_data.json"
        meta_path    = Path(output_dir) / "metadata.json"

        with open(resumes_path, "w", encoding="utf-8") as f:
            json.dump(resumes, f, indent=2, ensure_ascii=False)
        with open(jobs_path, "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False)
        with open(ner_path, "w", encoding="utf-8") as f:
            json.dump(ner_training_data, f, indent=2, ensure_ascii=False)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(dataset["metadata"], f, indent=2)

        print(f"[DataGen] [OK] Dataset saved to '{output_dir}/'")
        print(f"[DataGen]   - {resumes_path.name}: {len(resumes)} records")
        print(f"[DataGen]   - {jobs_path.name}:    {len(jobs)} records")
        print(f"[DataGen]   - {ner_path.name}: {len(ner_training_data)} annotated texts")

    return dataset


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parents[4]
    output   = base_dir / "datasets"
    generate_dataset(num_resumes=600, num_jobs=200, output_dir=str(output))
