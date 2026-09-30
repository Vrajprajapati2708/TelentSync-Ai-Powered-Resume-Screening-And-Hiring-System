# ============================================================
#  TalentSync — Application Factory  (app/__init__.py)
#  Creates and configures the Flask app, registers Blueprints,
#  initialises the database, and creates upload directories.
# ============================================================

import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.config.settings import ActiveConfig

# Global limiter instance (attached to app in create_app; reads RATELIMIT_STORAGE_URI from config)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],                 # No global default — apply per route
    in_memory_fallback_enabled=True,   # Emergency fallback when Redis is unreachable
)


def create_app(config=None) -> Flask:
    """
    Flask Application Factory.
    Call this function to create a configured Flask instance.
    """
    app = Flask(
        __name__,
        static_folder='static',
        template_folder='templates'
    )

    # ── Load configuration
    from app.config.settings import TestingConfig, _detect_testing
    cfg = config or (TestingConfig if _detect_testing() else ActiveConfig)
    app.config.from_object(cfg)
    app.secret_key = cfg.SECRET_KEY

    # ── Attach rate limiter
    limiter.init_app(app)

    # ── Ensure upload directories exist (isolated per config)
    upload_folder = app.config.get("UPLOAD_FOLDER", ActiveConfig.UPLOAD_FOLDER)
    temp_folder   = app.config.get("TEMP_FOLDER", ActiveConfig.TEMP_FOLDER)
    os.makedirs(upload_folder, exist_ok=True)
    os.makedirs(temp_folder,   exist_ok=True)

    # ── Register Blueprints
    from app.routes.auth_routes   import auth_bp
    from app.routes.resume_routes import resume_bp
    from app.routes.user_routes   import user_bp
    from app.routes.admin_routes  import admin_bp
    from app.routes.ml_routes     import ml_bp
    from app.routes.jobs_routes   import jobs_bp, jobs_v1_bp
    from app.routes.health_routes import health_bp
    from app.routes.platform_admin_routes import platform_admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(resume_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(ml_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(jobs_v1_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(platform_admin_bp)

    # ── Landing page route
    @app.route('/')
    def index():
        return render_template('index.html')

    # ── Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return jsonify({
            'success': False,
            'message': 'Too many requests. Please slow down and try again later.'
        }), 429

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/404.html'), 500

    # ── Security response headers (SEC-07)
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:; "
            "img-src 'self' data: https: blob:; "
            "connect-src 'self' https://api.adzuna.com; "
            "frame-ancestors 'none';"
        )
        return response

    # ── Initialise database on first run (isolated per config)
    db_file = app.config.get("DB_FILE", ActiveConfig.DB_FILE)
    os.makedirs(os.path.dirname(os.path.abspath(db_file)), exist_ok=True)
    _init_db(db_file)

    return app


# ── Database bootstrap ─────────────────────────────────────

def _init_db(db_file: str):
    """Create all tables and seed demo data if the DB is empty."""
    # If this is an isolated test database and not yet populated, seed it from pristine baseline backup
    if not os.path.exists(db_file) or os.path.getsize(db_file) == 0:
        backup_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'talentsync_backup_phase5.db')
        if os.path.abspath(db_file) != os.path.abspath(ActiveConfig.DB_FILE) and os.path.exists(backup_path):
            import shutil
            shutil.copy2(backup_path, db_file)
            return

    schema_path = os.path.join(os.path.dirname(__file__), 'database', 'schema.sql')

    with sqlite3.connect(db_file) as conn:
        # Create tables from schema file
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                conn.executescript(f.read())
        else:
            _create_tables_inline(conn)

        # Safe migration for existing tables missing new columns
        cols_users = [row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()]
        if 'is_verified' not in cols_users:
            conn.execute("ALTER TABLE users ADD COLUMN is_verified INTEGER DEFAULT 0")

        cols_resumes = [row[1] for row in conn.execute("PRAGMA table_info(resumes)").fetchall()]
        if 'structured_json' not in cols_resumes:
            conn.execute("ALTER TABLE resumes ADD COLUMN structured_json TEXT DEFAULT ''")

        _seed_demo_data(conn)
        conn.commit()


def _create_tables_inline(conn):
    """Fallback: create tables without the schema.sql file."""
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, email TEXT UNIQUE, password TEXT, role TEXT,
            skills TEXT DEFAULT '', ats_score INTEGER DEFAULT 0,
            phone TEXT DEFAULT '', location TEXT DEFAULT '',
            linkedin TEXT DEFAULT '', github TEXT DEFAULT '',
            summary TEXT DEFAULT '', education TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, company TEXT, location TEXT, type TEXT, salary TEXT,
            skills TEXT, description TEXT, status TEXT DEFAULT 'Active',
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, job_id INTEGER,
            match_score INTEGER DEFAULT 0, status TEXT DEFAULT 'Reviewing',
            applied_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(job_id)  REFERENCES jobs(id),
            UNIQUE(user_id, job_id)
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, title TEXT, message TEXT, type TEXT,
            is_read INTEGER DEFAULT 0, created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
    ''')


def _seed_demo_data(conn):
    """Insert demo users, jobs and applications if tables are empty."""
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        return   # Already seeded

    from werkzeug.security import generate_password_hash
    _demo_pw = generate_password_hash('demo123')

    demo_users = [
        ('Priya Mehta',   'priya@demo.com',   _demo_pw, 'hr',        '', 0),
    ]
    conn.executemany(
        "INSERT INTO users (name,email,password,role,skills,ats_score) VALUES (?,?,?,?,?,?)",
        demo_users
    )

    now = datetime.now().strftime('%Y-%m-%d')
    seed_jobs = [
        # ── Data Science & Analytics ──────────────────────────────────────────
        ('Data Scientist',              'Tata Consultancy Svcs','Bangalore',  'Full-time', '12-18 LPA',  'Python,Machine Learning,Pandas,SQL,Tableau,Scikit-Learn',                    'Senior Data Scientist role for TCS AI & Analytics practice. Build predictive models and data pipelines for enterprise clients.',  'Active',  now),
        ('Data Scientist II',           'Flipkart',             'Bangalore',  'Full-time', '18-25 LPA',  'Python,Machine Learning,Spark,SQL,A/B Testing,Statistics',                   'Work on recommendation systems and personalisation at scale for 400M users.',                                              'Active',  now),
        ('Data Scientist – NLP',        'Sarvam AI',            'Remote',     'Full-time', '20-30 LPA',  'Python,NLP,Transformers,PyTorch,BERT,Hugging Face',                          'Build and fine-tune large language models for Indian languages.',                                                         'Active',  now),
        ('Data Analyst',                'Scripbox',             'Bangalore',  'Full-time', '8-12 LPA',   'SQL,Excel,Tableau,Power BI,Data Science,Python',                             'Analyse investment and wealth data to create executive dashboards for stakeholders at India\'s leading robo-advisor.',   'Active',  now),
        ('Data Analyst – Growth',       'Swiggy',               'Bangalore',  'Full-time', '10-15 LPA',  'SQL,Python,Tableau,Excel,A/B Testing,Google Analytics',                      'Drive growth analytics for restaurant and delivery verticals.',                                                           'Active',  now),
        ('Senior Data Analyst',         'HDFC Bank',            'Mumbai',     'Full-time', '12-18 LPA',  'SQL,Python,SAS,Tableau,Power BI,Excel,Statistics',                           'Analyse credit risk, fraud patterns, and customer behaviour for retail banking.',                                         'Active',  now),
        ('Business Analyst',            'Fractal Analytics',    'Chennai',    'Full-time', '7-12 LPA',   'SQL,Excel,Power BI,Tableau,Data Science,JIRA',                               'Bridge business and technology — translate enterprise client requirements into actionable AI-driven insights at Fractal.', 'Active',  now),
        ('Business Intelligence Dev',   'Razorpay',             'Bangalore',  'Full-time', '14-20 LPA',  'SQL,Tableau,Power BI,Python,dbt,Redshift',                                   'Build BI dashboards and self-serve analytics platform used by 200+ internal stakeholders.',                               'Active',  now),
        ('Quantitative Analyst',        'Zerodha',              'Bangalore',  'Full-time', '20-35 LPA',  'Python,R,Statistics,Machine Learning,SQL,NumPy,SciPy',                       'Develop and back-test trading strategies using statistical and ML models.',                                               'Active',  now),
        ('Analytics Engineer',          'Meesho',               'Bangalore',  'Full-time', '15-22 LPA',  'Python,SQL,dbt,Airflow,BigQuery,Looker',                                     'Build the analytical layer between raw data and business dashboards.',                                                    'Active',  now),

        # ── Machine Learning & AI ─────────────────────────────────────────────
        ('ML Engineer',                 'Samsung R&D India',    'Bangalore',  'Full-time', '15-22 LPA',  'Python,TensorFlow,PyTorch,Docker,Deep Learning,MLflow',                      'Build and maintain production ML pipelines powering Samsung\'s on-device AI and Galaxy intelligence features.',          'Active',  now),
        ('ML Engineer – CV',            'Ola Electric',         'Bangalore',  'Full-time', '18-28 LPA',  'Python,Computer Vision,OpenCV,PyTorch,YOLO,CUDA',                            'Develop computer vision systems for autonomous driving and ADAS features.',                                               'Active',  now),
        ('Senior ML Engineer',          'Google India',         'Hyderabad',  'Full-time', '35-55 LPA',  'Python,TensorFlow,C++,Distributed Systems,Machine Learning,Kubernetes',      'Work on core ML infrastructure powering Google Search and Assistant.',                                                   'Active',  now),
        ('Applied Scientist',           'Amazon India',         'Bangalore',  'Full-time', '30-50 LPA',  'Python,Machine Learning,Statistics,NLP,PyTorch,Scala',                       'Drive applied science projects for Amazon\'s supply chain optimisation.',                                                 'Active',  now),
        ('AI Researcher',               'NVIDIA India',         'Hyderabad',  'Full-time', '20-30 LPA',  'Python,Machine Learning,NLP,Deep Learning,PyTorch,Research',                 'Conduct applied research in NLP and computer vision at NVIDIA\'s India AI research center in Hyderabad.',                'Active',  now),
        ('MLOps Engineer',              'PhonePe',              'Bangalore',  'Full-time', '18-26 LPA',  'Python,Kubernetes,Docker,MLflow,Airflow,AWS,Terraform',                      'Build the MLOps platform that deploys and monitors 150+ production models.',                                              'Active',  now),
        ('Generative AI Engineer',      'Infosys',              'Bangalore',  'Full-time', '16-24 LPA',  'Python,LangChain,OpenAI,RAG,Vector Databases,Hugging Face',                  'Build enterprise GenAI products using LLMs, RAG, and agent frameworks.',                                                 'Active',  now),
        ('Computer Vision Engineer',    'Niramai',              'Bangalore',  'Full-time', '12-20 LPA',  'Python,Computer Vision,OpenCV,PyTorch,TensorFlow,Medical Imaging',           'Apply deep learning for early-stage breast cancer detection from thermal images.',                                        'Active',  now),
        ('Conversational AI Engineer',  'Yellow.ai',            'Bangalore',  'Full-time', '14-22 LPA',  'Python,NLP,Rasa,DialogFlow,BERT,Machine Learning',                           'Build and improve the NLP engines powering enterprise chatbots.',                                                        'Active',  now),
        ('AI/ML Product Engineer',      'Freshworks',           'Chennai',    'Full-time', '15-22 LPA',  'Python,Machine Learning,TensorFlow,FastAPI,Docker,SQL',                      'Embed AI/ML features directly into CRM and ITSM SaaS products.',                                                        'Active',  now),

        # ── Data Engineering ──────────────────────────────────────────────────
        ('Data Engineer',               'Persistent Systems',   'Pune',       'Full-time', '10-16 LPA',  'Python,SQL,Spark,Hadoop,AWS,Docker,Airflow',                                 'Build robust, scalable data pipelines for Persistent Systems\' global digital engineering and cloud clients.',          'Active',  now),
        ('Senior Data Engineer',        'Juspay',               'Bangalore',  'Full-time', '20-30 LPA',  'Python,Scala,Spark,Kafka,Flink,AWS,Hive',                                    'Design and maintain real-time streaming pipelines for payments infrastructure.',                                           'Active',  now),
        ('Data Engineer – Streaming',   'Dunzo',                'Bangalore',  'Full-time', '12-18 LPA',  'Python,Kafka,Spark,Flink,AWS,Airflow,SQL',                                   'Build real-time data pipelines for hyperlocal delivery tracking and analytics.',                                          'Active',  now),
        ('Big Data Engineer',           'Mu Sigma',             'Bangalore',  'Full-time', '12-20 LPA',  'Python,Hadoop,Hive,Pig,Spark,SQL,AWS',                                       'Process petabyte-scale datasets for fortune 500 client analytics.',                                                     'Active',  now),
        ('ETL Developer',               'Capgemini',            'Mumbai',     'Full-time', '8-14 LPA',   'SQL,Python,Informatica,Talend,ETL,Data Warehousing',                         'Design and optimise ETL workflows for enterprise data warehouse migrations.',                                              'Active',  now),
        ('Platform Data Engineer',      'CRED',                 'Bangalore',  'Full-time', '18-28 LPA',  'Python,Spark,dbt,Airflow,Snowflake,Kafka,Terraform',                         'Own the data platform architecture serving analytics for 10M+ premium users.',                                           'Active',  now),

        # ── Cloud & Infrastructure ────────────────────────────────────────────
        ('Cloud Architect',             'NTT Data India',       'Bangalore',  'Full-time', '25-35 LPA',  'AWS,Azure,Docker,Kubernetes,Python,Terraform,Ansible',                       'Design and implement multi-cloud infrastructure for NTT Data\'s enterprise SaaS and managed services clients globally.', 'Active',  now),
        ('AWS Solutions Architect',     'Wipro',                'Hyderabad',  'Full-time', '20-32 LPA',  'AWS,EC2,S3,Lambda,VPC,CloudFormation,Terraform,Python',                      'Lead cloud migration and modernisation projects for large enterprise clients.',                                           'Active',  now),
        ('GCP Engineer',                'Thoughtworks',         'Bangalore',  'Full-time', '18-28 LPA',  'GCP,Kubernetes,Terraform,Python,BigQuery,Pub/Sub,Docker',                    'Build cloud-native solutions on Google Cloud for global clients.',                                                       'Active',  now),
        ('Azure DevOps Engineer',       'HCL Technologies',     'Noida',      'Full-time', '12-20 LPA',  'Azure,DevOps,Kubernetes,Docker,Terraform,CI/CD,Python',                      'Implement DevOps practices and Azure-based pipelines for banking clients.',                                               'Active',  now),
        ('Site Reliability Engineer',   'Zepto',                'Mumbai',     'Full-time', '22-32 LPA',  'Kubernetes,Docker,Prometheus,Grafana,Python,AWS,Terraform',                  'Ensure 99.99% uptime for 10-minute grocery delivery platform during peak hours.',                                        'Active',  now),
        ('Platform Engineer',           'Atlassian',            'Bangalore',  'Full-time', '30-45 LPA',  'Kubernetes,AWS,Terraform,Python,Go,CI/CD,Prometheus',                        'Build internal developer platform used by 10,000+ engineers worldwide.',                                                 'Active',  now),
        ('Infrastructure Engineer',     'ShareChat',            'Bangalore',  'Full-time', '18-28 LPA',  'AWS,Kubernetes,Terraform,Ansible,Python,Linux,Prometheus',                   'Scale infrastructure for India\'s largest vernacular social media platform.',                                              'Active',  now),

        # ── DevOps & CI/CD ────────────────────────────────────────────────────
        ('DevOps Engineer',             'Postman',              'Bangalore',  'Full-time', '16-24 LPA',  'Docker,Kubernetes,Jenkins,AWS,Terraform,Python,CI/CD,Git',                  'Automate deployment pipelines and manage Kubernetes clusters for Postman cloud.',                                        'Active',  now),
        ('Senior DevOps Engineer',      'BrowserStack',         'Mumbai',     'Full-time', '22-32 LPA',  'Docker,Kubernetes,AWS,GCP,Jenkins,Python,Terraform,Ansible',                 'Scale CI/CD infrastructure serving 50,000+ developers globally.',                                                        'Active',  now),
        ('DevSecOps Engineer',          'Paytm',                'Noida',      'Full-time', '18-26 LPA',  'Docker,Kubernetes,AWS,Security,SAST,DAST,Python,Jenkins',                   'Embed security into the DevOps pipeline for fintech products.',                                                          'Active',  now),
        ('Build & Release Engineer',    'Zoho Corporation',     'Chennai',    'Full-time', '10-18 LPA',  'Jenkins,Git,Maven,Docker,Linux,Shell Scripting,Python',                      'Manage build systems and release pipelines across 50+ Zoho products.',                                                  'Active',  now),

        # ── Backend Engineering ───────────────────────────────────────────────
        ('Python Developer',            'Zoho Corporation',     'Ahmedabad',  'Full-time', '6-10 LPA',   'Python,Django,Flask,PostgreSQL,Git,REST API',                                'Build scalable backend APIs and microservices for Zoho\'s 55+ cloud business applications used by 100M+ users.',        'Active',  now),
        ('Backend Engineer – Python',   'Groww',                'Bangalore',  'Full-time', '18-28 LPA',  'Python,FastAPI,PostgreSQL,Redis,Kafka,Docker,Kubernetes',                    'Build high-performance trading and portfolio APIs for 50M+ investors.',                                                  'Active',  now),
        ('Java Backend Developer',      'Infosys BPM',          'Pune',       'Full-time', '8-14 LPA',   'Java,Spring Boot,Hibernate,MySQL,REST API,Maven,Git',                        'Develop enterprise-grade microservices for global BPM clients.',                                                         'Active',  now),
        ('Senior Java Developer',       'Goldman Sachs',        'Bangalore',  'Full-time', '25-40 LPA',  'Java,Spring Boot,Kafka,PostgreSQL,Kubernetes,Low Latency',                   'Build ultra-low latency trading systems for global capital markets.',                                                    'Active',  now),
        ('Go Developer',                'Razorpay',             'Bangalore',  'Full-time', '20-30 LPA',  'Go,Golang,PostgreSQL,Redis,Kafka,Docker,Kubernetes,gRPC',                    'Develop core payment gateway components handling millions of TPS.',                                                      'Active',  now),
        ('Node.js Developer',           'Housing.com',          'Mumbai',     'Full-time', '10-16 LPA',  'Node.js,JavaScript,Express,MongoDB,Redis,AWS,REST API',                      'Build real-estate APIs serving 20M+ monthly users.',                                                                     'Active',  now),
        ('Scala/Spark Developer',       'Tata Digital',         'Mumbai',     'Full-time', '18-26 LPA',  'Scala,Spark,Kafka,AWS,SQL,Akka,Functional Programming',                      'Build data-intensive backend services for Tata Neu super-app.',                                                          'Active',  now),
        ('Ruby on Rails Developer',     'Helpshift',            'Bangalore',  'Full-time', '12-18 LPA',  'Ruby,Rails,PostgreSQL,Redis,AWS,Docker,Git',                                 'Build customer support SaaS platform features used by 600+ enterprise clients.',                                         'Active',  now),
        ('PHP Laravel Developer',       'InMobi',               'Bangalore',  'Full-time', '8-14 LPA',   'PHP,Laravel,MySQL,Redis,REST API,Git,Docker',                                'Develop ad-tech platform APIs and dashboards for the world\'s largest mobile DSP.',                                      'Active',  now),
        ('API Developer',               'MoEngage',             'Bangalore',  'Full-time', '14-22 LPA',  'Python,FastAPI,PostgreSQL,Redis,Kafka,Docker,REST API,gRPC',                 'Build customer engagement platform APIs used by 1200+ global brands.',                                                  'Active',  now),

        # ── Frontend Engineering ──────────────────────────────────────────────
        ('Frontend Developer',          'Mphasis',              'Delhi',      'Full-time', '6-11 LPA',   'React,JavaScript,HTML,CSS,Node.js,Git',                                      'Build pixel-perfect, accessible UIs for Mphasis\' banking and financial services enterprise web applications.',          'Active',  now),
        ('Senior Frontend Engineer',    'Zomato',               'Gurgaon',    'Full-time', '18-28 LPA',  'React,TypeScript,Redux,GraphQL,CSS,Webpack,Performance',                     'Drive frontend excellence for Zomato\'s restaurant discovery and ordering experience.',                                  'Active',  now),
        ('React Developer',             'Lenskart',             'Noida',      'Full-time', '10-16 LPA',  'React,JavaScript,TypeScript,Redux,CSS,Node.js,REST API',                     'Build e-commerce product pages and checkout flows for 20M+ shoppers.',                                                  'Active',  now),
        ('Vue.js Developer',            'Zendesk India',        'Hyderabad',  'Full-time', '12-18 LPA',  'Vue.js,JavaScript,TypeScript,CSS,HTML,REST API,Git',                         'Build customer-facing components for Zendesk\'s support suite products.',                                                'Active',  now),
        ('Angular Developer',           'Cognizant',            'Pune',       'Full-time', '8-14 LPA',   'Angular,TypeScript,JavaScript,HTML,CSS,RxJS,REST API',                       'Develop enterprise HR and supply chain management front-ends.',                                                          'Active',  now),
        ('UI Engineer',                 'Hotstar',              'Bangalore',  'Full-time', '16-24 LPA',  'React,TypeScript,WebGL,Video Streaming,Performance,CSS',                     'Build high-performance streaming UIs for India\'s #1 OTT platform.',                                                    'Active',  now),
        ('Next.js Developer',           'Dukaan',               'Bangalore',  'Full-time', '10-16 LPA',  'Next.js,React,TypeScript,CSS,Node.js,PostgreSQL,Vercel',                     'Build full-stack e-commerce storefronts for 4M+ merchants.',                                                            'Active',  now),

        # ── Full-Stack Engineering ────────────────────────────────────────────
        ('Full-Stack Developer',        'Chargebee',            'Chennai',    'Full-time', '12-18 LPA',  'React,Node.js,Python,PostgreSQL,AWS,Docker,REST API',                        'Build end-to-end subscription billing features for 6,500+ SaaS businesses.',                                            'Active',  now),
        ('Full-Stack Engineer – MERN',  'Unacademy',            'Bangalore',  'Full-time', '14-22 LPA',  'MongoDB,Express,React,Node.js,TypeScript,AWS,Redis',                         'Build learning platform features for 50M+ students across India.',                                                      'Active',  now),
        ('Full-Stack Engineer',         'Khatabook',            'Bangalore',  'Full-time', '14-20 LPA',  'React,Python,FastAPI,PostgreSQL,Redis,Docker,AWS',                            'Build digital accounting tools used by 10M+ small businesses.',                                                         'Active',  now),
        ('MEAN Stack Developer',        'Simpl',                'Bangalore',  'Full-time', '10-16 LPA',  'MongoDB,Express,Angular,Node.js,AWS,Docker,REST API',                        'Build buy-now-pay-later checkout experiences for 5M+ consumers.',                                                       'Active',  now),

        # ── Mobile Development ────────────────────────────────────────────────
        ('Android Developer',           'Ola',                  'Bangalore',  'Full-time', '12-20 LPA',  'Android,Kotlin,Java,MVVM,Retrofit,Room,Firebase',                            'Build and optimise the Ola ride-hailing Android app for 150M+ users.',                                                  'Active',  now),
        ('Senior Android Engineer',     'NPCI',                 'Mumbai',     'Full-time', '20-30 LPA',  'Android,Kotlin,MVVM,Coroutines,Jetpack Compose,Security',                    'Build UPI payment infrastructure for the national payments network.',                                                    'Active',  now),
        ('iOS Developer',               'Dream11',              'Mumbai',     'Full-time', '15-25 LPA',  'iOS,Swift,SwiftUI,Combine,Xcode,REST API,Firebase',                          'Build the iOS fantasy sports app for 160M+ users.',                                                                     'Active',  now),
        ('React Native Developer',      'Rapido',               'Bangalore',  'Full-time', '10-18 LPA',  'React Native,JavaScript,TypeScript,Redux,Firebase,Android,iOS',              'Build cross-platform bike taxi app for 25M+ commuters.',                                                                'Active',  now),
        ('Flutter Developer',           'Jupiter Money',        'Bangalore',  'Full-time', '12-20 LPA',  'Flutter,Dart,Firebase,REST API,Android,iOS,Riverpod',                        'Build a beautiful cross-platform neo-banking app with Dart and Flutter.',                                                'Active',  now),

        # ── NLP & Language AI ─────────────────────────────────────────────────
        ('NLP Engineer',                'Sarvam AI',            'Bangalore',  'Full-time', '18-26 LPA',  'Python,NLP,TensorFlow,PyTorch,Deep Learning,Transformers,BERT',              'Fine-tune and deploy production-grade large language models for Indian languages at Sarvam AI.',                          'Active',  now),
        ('NLP Research Engineer',       'IIT Bombay AI Lab',    'Mumbai',     'Full-time', '14-22 LPA',  'Python,NLP,PyTorch,Research,BERT,Transformers,Hugging Face',                 'Conduct research and build models for low-resource Indian language NLP.',                                                'Active',  now),
        ('Text Analytics Engineer',     'Genpact',              'Hyderabad',  'Full-time', '10-16 LPA',  'Python,NLP,spaCy,NLTK,Machine Learning,SQL,Tableau',                         'Extract insights from unstructured text data for banking and insurance clients.',                                        'Active',  now),

        # ── Cybersecurity ─────────────────────────────────────────────────────
        ('Cybersecurity Analyst',       'Wipro CyberDefense',   'Bangalore',  'Full-time', '10-18 LPA',  'SIEM,Network Security,Wireshark,Penetration Testing,Linux,Python',           'Monitor, detect, and respond to security incidents for enterprise clients 24x7.',                                        'Active',  now),
        ('Application Security Eng.',   'Razorpay',             'Bangalore',  'Full-time', '18-28 LPA',  'Penetration Testing,OWASP,Burp Suite,Python,SAST,DAST,Security',             'Secure payment APIs and applications through proactive security testing.',                                               'Active',  now),
        ('Cloud Security Engineer',     'Palo Alto Networks',   'Bangalore',  'Full-time', '25-40 LPA',  'AWS,Azure,GCP,Security,CSPM,IAM,Python,Terraform,SIEM',                      'Protect multi-cloud environments for enterprise clients across APAC.',                                                   'Active',  now),
        ('Security Operations Analyst', 'Quick Heal',           'Pune',       'Full-time', '8-14 LPA',   'Cybersecurity,SIEM,Splunk,Network Security,Linux,Incident Response',          'Operate the SOC and respond to malware, ransomware, and phishing threats.',                                              'Active',  now),

        # ── QA & Testing ──────────────────────────────────────────────────────
        ('SDET',                        'Testlio',              'Remote',     'Full-time', '10-18 LPA',  'Selenium,Python,Java,TestNG,API Testing,CI/CD,Docker',                       'Build automated test suites for global SaaS clients.',                                                                  'Active',  now),
        ('QA Automation Engineer',      'BrowserStack',         'Mumbai',     'Full-time', '12-20 LPA',  'Selenium,Python,Java,Cypress,API Testing,Appium,JIRA',                       'Automate end-to-end testing for BrowserStack\'s cloud testing platform.',                                                'Active',  now),
        ('Performance Test Engineer',   'Tata Consultancy',     'Pune',       'Full-time', '10-16 LPA',  'JMeter,LoadRunner,Python,SQL,Performance Testing,Grafana',                   'Design and execute load, stress, and performance tests for banking systems.',                                             'Active',  now),
        ('Manual QA Engineer',          'Freshworks',           'Chennai',    'Full-time', '6-10 LPA',   'Manual Testing,JIRA,SQL,API Testing,Postman,Regression Testing',              'Own quality for Freshdesk\'s customer support product across web and mobile.',                                           'Active',  now),

        # ── Database & Storage ────────────────────────────────────────────────
        ('Database Administrator',      'Nykaa',                'Mumbai',     'Full-time', '12-20 LPA',  'PostgreSQL,MySQL,MongoDB,Redis,AWS RDS,Performance Tuning,SQL',              'Manage and optimise databases powering 15M+ monthly active users.',                                                     'Active',  now),
        ('Elasticsearch Engineer',      'Sharechat',            'Bangalore',  'Full-time', '14-22 LPA',  'Elasticsearch,Kibana,Python,Logstash,AWS,Search,SQL',                        'Build and scale search and analytics infrastructure for 180M+ users.',                                                  'Active',  now),

        # ── Product Management ────────────────────────────────────────────────
        ('Product Manager',             'Razorpay',             'Bangalore',  'Full-time', '22-35 LPA',  'Product Management,SQL,Data Analysis,JIRA,Agile,User Research,Roadmap',      'Define and drive the product roadmap for payment gateway APIs.',                                                         'Active',  now),
        ('Associate Product Manager',   'Ola',                  'Bangalore',  'Full-time', '15-22 LPA',  'Product Management,SQL,Agile,JIRA,Data Analysis,Wireframing',                'Own product areas for Ola\'s driver and rider experience.',                                                              'Active',  now),
        ('Senior Product Manager',      'Hotstar',              'Mumbai',     'Full-time', '28-42 LPA',  'Product Management,Data Analysis,SQL,A/B Testing,Agile,OKRs',               'Lead product strategy for Hotstar\'s sports streaming experience.',                                                      'Active',  now),
        ('Technical Product Manager',   'Postman',              'Bangalore',  'Full-time', '25-38 LPA',  'Product Management,API,SQL,Python,Agile,Developer Tools,User Research',      'Define the roadmap for Postman API testing and collaboration features.',                                                 'Active',  now),

        # ── UI/UX Design ──────────────────────────────────────────────────────
        ('UI/UX Designer',              'Cleartax',             'Bangalore',  'Full-time', '8-14 LPA',   'Figma,Adobe XD,UI Design,UX Research,Prototyping,Design Systems',             'Design intuitive tax filing experiences for 5M+ Indian taxpayers.',                                                    'Active',  now),
        ('Senior Product Designer',     'Cred',                 'Bangalore',  'Full-time', '18-28 LPA',  'Figma,UI Design,UX Research,Interaction Design,Design Systems,Prototyping',  'Shape the premium design language for CRED\'s 9M+ credit card users.',                                                  'Active',  now),
        ('UX Researcher',               'Meesho',               'Bangalore',  'Full-time', '14-22 LPA',  'UX Research,User Interviews,Usability Testing,Figma,Data Analysis',          'Conduct qualitative and quantitative research for Bharat\'s largest social commerce platform.',                          'Active',  now),
        ('Motion Designer',             'Byju\'s',              'Bangalore',  'Full-time', '8-14 LPA',   'After Effects,Figma,Motion Design,Animation,Illustrator,Photoshop',           'Create engaging motion graphics and animations for EdTech learning content.',                                            'Closing', now),

        # ── Embedded / Hardware / IoT ─────────────────────────────────────────
        ('Embedded Systems Engineer',   'Ather Energy',         'Bangalore',  'Full-time', '12-20 LPA',  'C,C++,Embedded Systems,RTOS,CAN Bus,Linux,Python',                           'Develop firmware for Ather\'s next-generation electric scooter ECUs.',                                                  'Active',  now),
        ('IoT Engineer',                'Bosch India',          'Bangalore',  'Full-time', '10-18 LPA',  'IoT,C,Python,MQTT,AWS IoT,Embedded Linux,Node.js',                           'Build connected-device solutions for automotive and smart building verticals.',                                          'Active',  now),
        ('VLSI Design Engineer',        'Intel India',          'Hyderabad',  'Full-time', '15-25 LPA',  'VLSI,Verilog,SystemVerilog,FPGA,Synthesis,Simulation,C++',                   'Design and verify high-performance CPU and GPU silicon at Intel\'s India R&D center.',                                  'Active',  now),
        ('Robotics Engineer',           'AgniKul Cosmos',       'Chennai',    'Full-time', '12-22 LPA',  'Python,C++,ROS,Control Systems,MATLAB,Embedded Systems,Simulation',          'Build guidance, navigation, and control software for small-lift orbital rockets.',                                       'Active',  now),

        # ── Blockchain ────────────────────────────────────────────────────────
        ('Blockchain Developer',        'Polygon Labs',         'Remote',     'Full-time', '20-35 LPA',  'Solidity,Ethereum,Web3.js,Smart Contracts,Python,JavaScript,DeFi',           'Build and audit smart contracts for Polygon\'s Layer-2 blockchain ecosystem.',                                           'Active',  now),
        ('Web3 Backend Engineer',       'CoinDCX',              'Mumbai',     'Full-time', '18-28 LPA',  'Python,Node.js,Solidity,Web3,Blockchain,PostgreSQL,Docker',                  'Build crypto exchange backend infrastructure handling millions in daily volume.',                                        'Active',  now),

        # ── Technical Writing & Support ───────────────────────────────────────
        ('Technical Writer',            'Postman',              'Bangalore',  'Full-time', '8-14 LPA',   'Technical Writing,API Documentation,Markdown,REST API,Git,Swagger',          'Write world-class API documentation and tutorials for 25M+ developers.',                                                'Active',  now),
        ('Developer Relations Eng.',    'Twilio India',         'Bangalore',  'Full-time', '16-25 LPA',  'Python,Node.js,REST API,Technical Writing,Public Speaking,Git',              'Build sample apps, write tutorials, and represent Twilio at developer events.',                                          'Active',  now),

        # ── Research & Emerging Tech ──────────────────────────────────────────
        ('Research Scientist – AI',     'Microsoft Research',   'Hyderabad',  'Full-time', '35-60 LPA',  'Python,Machine Learning,Deep Learning,Research,PyTorch,Statistics',          'Conduct fundamental and applied AI research at Microsoft\'s India lab.',                                                'Active',  now),
        ('Quantum Computing Engineer',  'IBM India',            'Bangalore',  'Full-time', '25-40 LPA',  'Python,Qiskit,Linear Algebra,Quantum Computing,Machine Learning',            'Develop quantum algorithms and hybrid classical-quantum machine learning models.',                                       'Active',  now),

        # ── EdTech ────────────────────────────────────────────────────────────
        ('EdTech Product Engineer',     'Byju\'s',              'Bangalore',  'Full-time', '12-20 LPA',  'Python,React,Node.js,PostgreSQL,Machine Learning,AWS',                       'Build adaptive learning engines personalising content for 150M+ students.',                                              'Active',  now),
        ('Curriculum Data Scientist',   'Scaler Academy',       'Bangalore',  'Full-time', '14-22 LPA',  'Python,SQL,Machine Learning,Data Analysis,A/B Testing,Excel',                'Use data to measure learning outcomes and optimise curriculum for tech learners.',                                        'Active',  now),

        # ── FinTech ───────────────────────────────────────────────────────────
        ('FinTech Backend Engineer',    'Fi Money',             'Bangalore',  'Full-time', '16-24 LPA',  'Python,Go,PostgreSQL,Kafka,Docker,AWS,Redis,Microservices',                  'Build core banking APIs for Fi\'s mobile-first neobank.',                                                               'Active',  now),
        ('Risk & Fraud Data Scientist', 'Paytm',                'Noida',      'Full-time', '16-24 LPA',  'Python,Machine Learning,SQL,Fraud Detection,Statistics,Spark',               'Build real-time fraud detection models protecting 330M+ users.',                                                        'Active',  now),
        ('Algorithmic Trading Dev',     'Groww',                'Bangalore',  'Full-time', '20-32 LPA',  'Python,C++,Algorithms,Low Latency,Machine Learning,SQL,Kafka',               'Build algorithmic and automated trading systems for retail investors.',                                                 'Active',  now),
        ('Compliance Tech Engineer',    'Stripe India',         'Bangalore',  'Full-time', '20-32 LPA',  'Python,Java,SQL,Regulatory Tech,AWS,Machine Learning,REST API',              'Build automated compliance and KYC pipelines for Stripe\'s global payments.',                                           'Active',  now),

        # ── HealthTech ────────────────────────────────────────────────────────
        ('HealthTech Software Engineer','Practo',               'Bangalore',  'Full-time', '12-20 LPA',  'Python,Django,PostgreSQL,React,Docker,AWS,Machine Learning',                 'Build digital health products connecting 100M+ patients with 100K+ doctors.',                                           'Active',  now),
        ('Medical AI Engineer',         'Niramai Health',       'Bangalore',  'Full-time', '14-22 LPA',  'Python,Deep Learning,Medical Imaging,TensorFlow,OpenCV,Research',            'Apply AI to non-invasive cancer detection with thermal imaging and ML.',                                                'Active',  now),

        # ── AgriTech ──────────────────────────────────────────────────────────
        ('AgriTech Data Scientist',     'DeHaat',               'Patna',      'Full-time', '10-18 LPA',  'Python,Machine Learning,Satellite Imaging,SQL,Computer Vision,GIS',          'Build AI models for crop yield prediction and precision farming for 1M+ farmers.',                                      'Active',  now),

        # ── Other Domains ─────────────────────────────────────────────────────
        ('Scrum Master',                'Accenture',            'Hyderabad',  'Full-time', '10-18 LPA',  'Agile,Scrum,JIRA,Confluence,Kanban,Sprint Planning,Stakeholder Mgmt',        'Facilitate agile ceremonies and remove impediments for 3 cross-functional squads.',                                      'Active',  now),
        ('Technical Recruiter',         'Naukri.com',           'Noida',      'Full-time', '6-11 LPA',   'Recruiting,LinkedIn,Boolean Search,ATS,Communication,HR',                    'Source and hire top engineering talent for India\'s largest job portal.',                                               'Closing', now),
        ('Solutions Engineer',          'Salesforce India',     'Hyderabad',  'Full-time', '18-28 LPA',  'Salesforce,CRM,JavaScript,Apex,REST API,SQL,Solution Architecture',           'Design and demo Salesforce solutions for enterprise prospects in APAC.',                                                'Active',  now),
        ('SAP ABAP Developer',          'Deloitte India',       'Pune',       'Full-time', '10-18 LPA',  'SAP,ABAP,SD,MM,FI,BAPI,ALV,OData',                                          'Develop custom SAP ABAP programs for global manufacturing clients.',                                                    'Active',  now),
        ('Game Developer',              'Nazara Technologies',  'Mumbai',     'Full-time', '10-18 LPA',  'Unity,C#,C++,Game Development,Mobile Games,Shaders,Physics',                 'Build engaging mobile games for India\'s largest listed gaming company.',                                                'Active',  now),
        ('AR/VR Developer',             'Jio',                  'Mumbai',     'Full-time', '14-22 LPA',  'Unity,C#,AR,VR,ARKit,ARCore,3D Modelling,Unreal Engine',                    'Build immersive AR/VR experiences for JioGlass and enterprise metaverse projects.',                                     'Active',  now),
    ]
    conn.executemany(
        "INSERT INTO jobs (title,company,location,type,salary,skills,description,status,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        seed_jobs
    )


    apps = []
    conn.executemany(
        "INSERT INTO applications (user_id,job_id,match_score,status,applied_at) VALUES (?,?,?,?,?)",
        apps
    )
