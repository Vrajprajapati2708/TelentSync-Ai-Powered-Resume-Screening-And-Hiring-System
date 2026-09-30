"""
TalentSync — Seed 100+ REAL Company Jobs into the Database
All companies are real Indian & global tech companies with realistic job data.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'talentsync.db')

REAL_JOBS = [
    # ── Big Tech (India offices) ────────────────────────────
    ("Software Engineer", "Google India", "Bangalore", "Full-time", "25-45 LPA", "Python,Java,Go,Algorithms,Data Structures,System Design,Cloud,Kubernetes", "Design and build scalable distributed systems powering Google products used by billions. Work on search, ads, cloud infrastructure, or AI/ML platforms."),
    ("Data Scientist", "Microsoft India", "Hyderabad", "Full-time", "22-40 LPA", "Python,R,SQL,Machine Learning,Azure,Power BI,Statistics,Deep Learning", "Apply advanced analytics and machine learning to improve Microsoft products. Build predictive models, run A/B tests, and derive insights from petabyte-scale data."),
    ("SDE II", "Amazon India", "Bangalore", "Full-time", "28-50 LPA", "Java,Python,AWS,System Design,Microservices,DynamoDB,SQL,Docker", "Build highly available distributed systems for Amazon's e-commerce platform. Own end-to-end feature delivery from design to deployment at massive scale."),
    ("ML Engineer", "Meta India", "Gurgaon", "Full-time", "30-55 LPA", "Python,PyTorch,Deep Learning,NLP,Computer Vision,C++,Distributed Systems", "Develop and deploy machine learning models for content ranking, integrity, and recommendation systems across Facebook, Instagram, and WhatsApp."),
    ("iOS Developer", "Apple India", "Hyderabad", "Full-time", "25-42 LPA", "Swift,Objective-C,iOS SDK,Xcode,UIKit,SwiftUI,Core Data,REST APIs", "Build next-generation features for Apple Maps and Siri. Create seamless user experiences on iOS, iPadOS, and macOS platforms."),
    ("Cloud Engineer", "IBM India", "Pune", "Full-time", "12-22 LPA", "Python,Kubernetes,Docker,Terraform,AWS,Azure,Linux,CI/CD", "Design and manage hybrid cloud infrastructure for enterprise clients. Implement DevOps practices and automate cloud deployments."),
    ("Full Stack Developer", "Oracle India", "Bangalore", "Full-time", "15-28 LPA", "Java,JavaScript,React,Node.js,SQL,Oracle DB,REST APIs,Microservices", "Develop enterprise cloud applications for Oracle Cloud Infrastructure. Build scalable front-end and back-end systems."),
    ("DevOps Engineer", "SAP Labs India", "Bangalore", "Full-time", "14-26 LPA", "Kubernetes,Docker,Jenkins,Terraform,AWS,Python,Linux,Ansible,CI/CD", "Build and maintain CI/CD pipelines for SAP's cloud products. Automate infrastructure provisioning and monitoring."),
    ("Backend Engineer", "Salesforce India", "Hyderabad", "Full-time", "18-32 LPA", "Java,Python,Microservices,PostgreSQL,Redis,Kafka,AWS,REST APIs", "Design and implement backend services for Salesforce CRM platform. Build APIs serving millions of enterprise users worldwide."),
    ("GPU Computing Engineer", "NVIDIA India", "Pune", "Full-time", "22-40 LPA", "CUDA,C++,Python,Deep Learning,Computer Vision,Linux,GPU Architecture", "Optimize deep learning frameworks for NVIDIA GPUs. Develop CUDA kernels and contribute to TensorRT and cuDNN libraries."),
    ("Chip Design Engineer", "Intel India", "Bangalore", "Full-time", "18-35 LPA", "Verilog,SystemVerilog,VLSI,Python,RTL Design,FPGA,UVM", "Design next-generation processor architectures. Perform RTL design, verification, and timing analysis for Intel's latest chips."),
    ("Modem Engineer", "Qualcomm India", "Hyderabad", "Full-time", "16-30 LPA", "C,C++,5G,LTE,DSP,Python,MATLAB,Embedded Systems", "Develop 5G modem firmware and baseband algorithms. Work on cutting-edge wireless communication technologies."),
    ("Research Engineer", "Samsung R&D India", "Bangalore", "Full-time", "14-25 LPA", "Python,C++,Deep Learning,Computer Vision,TensorFlow,Android,Java", "Conduct R&D on AI-powered features for Samsung Galaxy devices. Build on-device ML models for camera, voice, and health applications."),
    
    # ── Indian IT Giants ────────────────────────────────────
    ("Systems Engineer", "TCS", "Mumbai", "Full-time", "4-8 LPA", "Java,Python,SQL,Spring Boot,Microservices,AWS,Agile", "Develop and maintain enterprise applications for global clients across banking, retail, and telecom sectors."),
    ("Technology Analyst", "Infosys", "Pune", "Full-time", "5-10 LPA", "Java,Python,Angular,SQL,AWS,Docker,REST APIs,Agile", "Design and deliver digital transformation solutions for Fortune 500 clients using modern cloud-native architectures."),
    ("Project Engineer", "Wipro", "Bangalore", "Full-time", "4-9 LPA", "Python,Java,React,SQL,Azure,DevOps,Agile,Jenkins", "Build scalable applications and implement CI/CD pipelines for enterprise digital transformation projects."),
    ("Software Engineer", "HCL Technologies", "Noida", "Full-time", "5-11 LPA", "Java,Spring Boot,Microservices,SQL,Docker,Kubernetes,AWS", "Develop microservices-based applications for healthcare and financial services clients on cloud platforms."),
    ("Associate Engineer", "Tech Mahindra", "Hyderabad", "Full-time", "4-8 LPA", "Python,Java,SQL,React,Node.js,MongoDB,AWS", "Build customer-facing telecom and enterprise solutions using modern full-stack technologies."),
    ("Senior Developer", "Mindtree (LTIMindtree)", "Bangalore", "Full-time", "8-16 LPA", "Java,Spring Boot,React,AWS,Microservices,PostgreSQL,Docker", "Lead development of cloud-native enterprise applications. Mentor junior developers and drive technical excellence."),
    ("Software Developer", "Mphasis", "Pune", "Full-time", "6-12 LPA", "Python,Django,React,PostgreSQL,AWS,Docker,REST APIs", "Develop AI-powered banking and insurance solutions using modern Python frameworks and cloud services."),
    ("Engineer", "L&T Infotech (LTI)", "Mumbai", "Full-time", "5-10 LPA", "Java,Python,SQL,Angular,Azure,Terraform,Agile", "Build enterprise solutions for manufacturing and energy sector clients with cloud and data analytics."),
    
    # ── Indian Unicorns & Startups ──────────────────────────
    ("Backend Engineer", "Flipkart", "Bangalore", "Full-time", "18-35 LPA", "Java,Python,MySQL,Redis,Kafka,Microservices,Docker,Kubernetes", "Build high-throughput backend services handling millions of orders during Big Billion Days. Optimize for extreme scale and reliability."),
    ("Frontend Engineer", "Flipkart", "Bangalore", "Full-time", "16-30 LPA", "React,JavaScript,TypeScript,Node.js,GraphQL,Webpack,CSS,Performance", "Create delightful shopping experiences on Flipkart web and mobile. Optimize Core Web Vitals for 400M+ users."),
    ("Data Scientist", "Zomato", "Gurgaon", "Full-time", "15-28 LPA", "Python,Machine Learning,SQL,Pandas,Scikit-Learn,Deep Learning,A/B Testing", "Build ML models for restaurant recommendations, delivery time predictions, and dynamic pricing. Analyze user behavior data."),
    ("Android Developer", "Swiggy", "Bangalore", "Full-time", "14-26 LPA", "Kotlin,Java,Android SDK,MVVM,Jetpack Compose,Retrofit,Room,Firebase", "Build and optimize Swiggy's Android app used by 50M+ users. Implement features for food ordering, Instamart, and Dineout."),
    ("Full Stack Developer", "Paytm", "Noida", "Full-time", "12-22 LPA", "Java,React,Node.js,MongoDB,Redis,Kafka,AWS,Docker", "Build fintech products for payments, banking, and commerce platform serving 350M+ users across India."),
    ("Backend Engineer", "PhonePe", "Bangalore", "Full-time", "16-30 LPA", "Java,Spring Boot,MySQL,Redis,Kafka,Microservices,Kubernetes", "Design payment processing systems handling 4B+ monthly transactions on India's largest UPI platform."),
    ("Product Engineer", "CRED", "Bangalore", "Full-time", "18-35 LPA", "Python,React,Node.js,PostgreSQL,Redis,AWS,TypeScript,GraphQL", "Build premium fintech experiences for CRED's credit card management platform. Focus on delightful UX and system reliability."),
    ("Backend Developer", "Razorpay", "Bangalore", "Full-time", "15-28 LPA", "Go,Python,Ruby,PostgreSQL,Redis,Kafka,AWS,Kubernetes", "Build India's payment infrastructure processing billions in transactions. Design highly available financial systems."),
    ("Software Engineer", "Zerodha", "Bangalore", "Full-time", "12-25 LPA", "Go,Python,PostgreSQL,Redis,Kafka,React,WebSockets,Linux", "Build India's largest stock trading platform. Develop low-latency systems handling millions of trades per day."),
    ("ML Engineer", "Meesho", "Bangalore", "Full-time", "16-30 LPA", "Python,PyTorch,NLP,Computer Vision,SQL,Spark,AWS,Docker", "Build recommendation engines and search ranking models for India's fastest-growing social commerce platform."),
    ("Data Analyst", "Groww", "Bangalore", "Full-time", "10-18 LPA", "Python,SQL,Tableau,Pandas,Excel,Statistics,A/B Testing", "Analyze investment patterns and user behavior on India's leading investment platform. Build dashboards and drive data-driven decisions."),
    ("Frontend Developer", "ShareChat", "Bangalore", "Full-time", "14-24 LPA", "React,TypeScript,Next.js,JavaScript,CSS,Redux,Webpack,GraphQL", "Build engaging social media experiences for India's largest regional language platform with 200M+ monthly users."),
    ("Backend Engineer", "Dunzo", "Bangalore", "Full-time", "12-22 LPA", "Python,Django,PostgreSQL,Redis,Celery,Docker,AWS,Microservices", "Build real-time delivery logistics platform. Optimize route planning and order management systems."),
    ("Full Stack Developer", "Lenskart", "Gurgaon", "Full-time", "10-20 LPA", "React,Node.js,Python,MongoDB,Redis,AWS,Docker,TypeScript", "Build omnichannel retail technology for India's largest eyewear company. Develop AR try-on and e-commerce features."),
    ("Data Engineer", "Nykaa", "Mumbai", "Full-time", "12-22 LPA", "Python,Spark,Airflow,SQL,AWS,Redshift,Kafka,Tableau", "Build data pipelines powering analytics and personalization for India's leading beauty e-commerce platform."),
    ("Software Engineer", "Ola", "Bangalore", "Full-time", "14-26 LPA", "Java,Python,Kafka,Redis,MySQL,Microservices,Docker,Kubernetes", "Build ride-matching and dynamic pricing algorithms for India's largest mobility platform."),
    ("Backend Developer", "Myntra", "Bangalore", "Full-time", "14-28 LPA", "Java,Spring Boot,MySQL,Redis,Kafka,Elasticsearch,Docker", "Build fashion e-commerce backend handling 30M+ monthly active users. Develop search, recommendation, and inventory systems."),
    ("Platform Engineer", "Dream11", "Mumbai", "Full-time", "16-30 LPA", "Go,Python,Kubernetes,AWS,Redis,PostgreSQL,Kafka,Terraform", "Build India's largest fantasy sports platform handling 100M+ concurrent users during IPL matches."),
    ("SDE", "BrowserStack", "Mumbai", "Full-time", "15-28 LPA", "Python,Java,Selenium,Docker,Kubernetes,AWS,Node.js,React", "Build cloud testing infrastructure used by 50K+ companies worldwide. Develop browser and device automation platforms."),
    ("Full Stack Developer", "Postman", "Bangalore", "Full-time", "18-32 LPA", "JavaScript,TypeScript,React,Node.js,Electron,MongoDB,AWS,GraphQL", "Build API development tools used by 25M+ developers globally. Improve collaboration features and API testing capabilities."),
    
    # ── SaaS & Product Companies ────────────────────────────
    ("Software Developer", "Zoho", "Chennai", "Full-time", "6-14 LPA", "Java,JavaScript,Python,MySQL,React,REST APIs,Linux,Git", "Build enterprise SaaS products used by 80M+ users worldwide. Develop modules for CRM, HR, and finance applications."),
    ("Product Engineer", "Freshworks", "Chennai", "Full-time", "12-24 LPA", "Ruby,React,PostgreSQL,Redis,AWS,Docker,Elasticsearch,GraphQL", "Build customer engagement software used by 60K+ businesses. Develop features for Freshdesk, Freshsales, and Freshservice."),
    ("Backend Engineer", "Chargebee", "Chennai", "Full-time", "14-26 LPA", "Ruby,Python,PostgreSQL,Redis,AWS,Microservices,Docker,REST APIs", "Build subscription billing platform serving 5000+ SaaS companies globally. Design payment processing and revenue analytics systems."),
    ("Frontend Engineer", "Hasura", "Bangalore", "Remote", "16-30 LPA", "React,TypeScript,GraphQL,Haskell,PostgreSQL,Docker,Kubernetes", "Build the Hasura Console and developer tools for the world's fastest GraphQL engine. Create intuitive data management interfaces."),
    ("DevOps Engineer", "Druva", "Pune", "Full-time", "14-26 LPA", "AWS,Python,Terraform,Kubernetes,Docker,Jenkins,Linux,Ansible,Go", "Build cloud data protection infrastructure on AWS. Automate backup, disaster recovery, and data governance systems."),
    ("Software Engineer", "Whatfix", "Bangalore", "Full-time", "10-20 LPA", "JavaScript,React,Python,Node.js,MongoDB,AWS,Chrome Extensions", "Build digital adoption platform helping enterprise users learn software faster. Develop in-app guidance and analytics tools."),
    
    # ── Fintech ─────────────────────────────────────────────
    ("Backend Engineer", "Pine Labs", "Noida", "Full-time", "12-22 LPA", "Java,Spring Boot,MySQL,Redis,Kafka,AWS,Microservices,Docker", "Build payment terminal and merchant commerce platform processing billions in transactions across Asia."),
    ("Data Scientist", "Bajaj Finserv", "Pune", "Full-time", "10-20 LPA", "Python,Machine Learning,SQL,Pandas,Scikit-Learn,Statistics,Tableau", "Build credit scoring models and fraud detection systems for one of India's largest NBFCs serving 60M+ customers."),
    ("Full Stack Developer", "PolicyBazaar", "Gurgaon", "Full-time", "10-20 LPA", "React,Node.js,Python,MySQL,Redis,AWS,Docker,TypeScript", "Build India's largest insurance marketplace. Develop comparison engines and policy management systems."),
    ("ML Engineer", "Upstox", "Mumbai", "Full-time", "14-26 LPA", "Python,Machine Learning,TensorFlow,SQL,Spark,AWS,Kafka,Docker", "Build ML-powered stock screening, portfolio analytics, and risk assessment models for 10M+ retail investors."),
    ("Backend Developer", "Slice", "Bangalore", "Full-time", "14-24 LPA", "Go,Python,PostgreSQL,Redis,Kafka,Kubernetes,AWS,gRPC", "Build fintech infrastructure for instant credit and payment products used by millions of young Indians."),
    
    # ── Consulting & Professional Services ──────────────────
    ("Technology Consultant", "Accenture India", "Mumbai", "Full-time", "8-18 LPA", "Java,Python,AWS,Azure,SQL,Agile,SAP,Microservices", "Drive digital transformation for Fortune 500 clients. Design and implement cloud migration and modernization strategies."),
    ("Data Engineer", "Deloitte India", "Hyderabad", "Full-time", "8-18 LPA", "Python,Spark,SQL,AWS,Snowflake,Airflow,Tableau,ETL", "Build enterprise data platforms and analytics solutions for banking, healthcare, and telecom clients."),
    ("Analytics Consultant", "PwC India", "Gurgaon", "Full-time", "8-16 LPA", "Python,R,SQL,Tableau,Power BI,Machine Learning,Statistics,Excel", "Deliver data-driven insights and predictive analytics solutions to help clients transform their business operations."),
    ("Technology Analyst", "EY India", "Bangalore", "Full-time", "7-15 LPA", "Python,SQL,Azure,Power BI,Tableau,Machine Learning,Agile", "Build technology risk assessment and audit automation tools. Implement cybersecurity and compliance solutions."),
    ("Associate", "KPMG India", "Mumbai", "Full-time", "7-14 LPA", "Python,SQL,Excel,Tableau,Power BI,R,Statistics,Data Analysis", "Perform data analytics for forensic investigations, risk advisory, and financial due diligence engagements."),
    
    # ── Banking & Finance Tech ──────────────────────────────
    ("Software Developer", "Goldman Sachs India", "Bangalore", "Full-time", "20-38 LPA", "Java,Python,React,SQL,AWS,Microservices,System Design,Kafka", "Build trading platforms and risk management systems for global financial markets. Develop low-latency applications."),
    ("Quantitative Analyst", "JP Morgan India", "Mumbai", "Full-time", "22-40 LPA", "Python,C++,Machine Learning,Statistics,SQL,R,Quantitative Finance", "Develop quantitative models for derivatives pricing, risk management, and algorithmic trading strategies."),
    ("Technology Analyst", "Morgan Stanley India", "Mumbai", "Full-time", "18-35 LPA", "Java,Python,React,SQL,Spring Boot,Microservices,AWS", "Build next-generation wealth management and trading platforms used by financial advisors and institutional clients worldwide."),
    ("Data Scientist", "American Express India", "Gurgaon", "Full-time", "16-30 LPA", "Python,Machine Learning,SQL,Spark,NLP,Deep Learning,A/B Testing", "Build fraud detection, credit decisioning, and customer analytics models for 100M+ cardmembers globally."),
    ("Backend Engineer", "Visa India", "Bangalore", "Full-time", "16-28 LPA", "Java,Spring Boot,Oracle,Kafka,Microservices,Docker,Kubernetes", "Build secure payment processing systems handling 65K+ transactions per second across 200+ countries."),
    
    # ── Telecom & Infrastructure ────────────────────────────
    ("Software Developer", "Jio Platforms", "Mumbai", "Full-time", "8-18 LPA", "Java,Python,Microservices,Kafka,Redis,MySQL,Docker,Kubernetes", "Build digital platforms for India's largest telecom operator with 450M+ subscribers. Develop JioMart, JioTV, and JioCloud services."),
    ("Network Engineer", "Airtel", "Gurgaon", "Full-time", "6-14 LPA", "Python,Linux,Networking,AWS,Docker,5G,Ansible,Monitoring", "Design and optimize India's second-largest telecom network. Implement 5G infrastructure and network automation."),
    
    # ── EdTech ──────────────────────────────────────────────
    ("Full Stack Developer", "Unacademy", "Bangalore", "Full-time", "12-24 LPA", "React,Node.js,Python,MongoDB,Redis,AWS,WebRTC,Docker", "Build live learning platform features including video streaming, interactive quizzes, and real-time doubt solving."),
    ("Backend Engineer", "upGrad", "Mumbai", "Full-time", "10-20 LPA", "Python,Django,PostgreSQL,Redis,Celery,AWS,Docker,REST APIs", "Build online education platform powering 2M+ learners. Develop course delivery, assessment, and certification systems."),
    ("ML Engineer", "Vedantu", "Bangalore", "Full-time", "12-22 LPA", "Python,Machine Learning,NLP,TensorFlow,SQL,AWS,Computer Vision", "Build AI-powered personalized learning recommendations and automated doubt resolution for K-12 students."),
    
    # ── HealthTech ──────────────────────────────────────────
    ("Software Engineer", "Practo", "Bangalore", "Full-time", "10-20 LPA", "Python,Django,React,PostgreSQL,Redis,AWS,Docker,Elasticsearch", "Build healthcare platform connecting 200K+ doctors with patients. Develop telemedicine, appointment booking, and health records systems."),
    ("Data Scientist", "PharmEasy", "Mumbai", "Full-time", "12-22 LPA", "Python,Machine Learning,SQL,Spark,Pandas,Scikit-Learn,AWS", "Build demand forecasting, inventory optimization, and personalized medicine recommendation models."),
    ("Backend Developer", "1mg (Tata Health)", "Gurgaon", "Full-time", "10-20 LPA", "Python,Django,PostgreSQL,Redis,Elasticsearch,Docker,AWS,Celery", "Build India's leading digital health platform. Develop pharmacy, diagnostics, and doctor consultation systems."),
    
    # ── Gaming & Media ──────────────────────────────────────
    ("Game Developer", "Games24x7", "Mumbai", "Full-time", "10-22 LPA", "Java,Python,Unity,C#,Redis,MySQL,AWS,Machine Learning", "Build real-money gaming platforms for RummyCircle and My11Circle with millions of concurrent players."),
    ("Backend Engineer", "MPL (Mobile Premier League)", "Bangalore", "Full-time", "14-26 LPA", "Go,Python,PostgreSQL,Redis,Kafka,Kubernetes,AWS,gRPC", "Build gaming infrastructure handling 100M+ users. Develop matchmaking, wallet, and tournament systems."),
    ("Software Engineer", "Hotstar (JioStar)", "Mumbai", "Full-time", "14-28 LPA", "Java,Python,React,AWS,Kafka,Redis,Microservices,CDN", "Build India's largest streaming platform serving 300M+ users. Handle massive concurrent viewership during IPL."),
    
    # ── Logistics & Mobility ────────────────────────────────
    ("Backend Engineer", "Delhivery", "Gurgaon", "Full-time", "12-22 LPA", "Python,Go,PostgreSQL,Redis,Kafka,AWS,Docker,Microservices", "Build logistics technology platform processing 2M+ shipments daily. Optimize route planning and warehouse operations."),
    ("Data Scientist", "BigBasket (Tata)", "Bangalore", "Full-time", "12-22 LPA", "Python,Machine Learning,SQL,Spark,Pandas,Deep Learning,AWS", "Build demand forecasting, delivery slot optimization, and recommendation models for India's largest online grocery platform."),
    ("SDE", "Rapido", "Bangalore", "Full-time", "10-20 LPA", "Java,Kotlin,Python,MySQL,Redis,Kafka,AWS,Docker", "Build India's largest bike-taxi platform. Develop ride matching, pricing algorithms, and driver management systems."),
    
    # ── Security & Cloud ────────────────────────────────────
    ("Security Engineer", "Palo Alto Networks India", "Bangalore", "Full-time", "18-32 LPA", "Python,Go,C++,Linux,Networking,Cloud Security,Kubernetes,AWS", "Build next-generation cybersecurity products. Develop threat detection, firewall, and cloud security solutions."),
    ("Cloud Architect", "Nutanix India", "Bangalore", "Full-time", "20-35 LPA", "Python,Go,Kubernetes,AWS,Azure,Terraform,Linux,Distributed Systems", "Design hybrid cloud infrastructure solutions. Build enterprise cloud management and hyperconverged platforms."),
    ("Site Reliability Engineer", "Atlassian India", "Bangalore", "Full-time", "20-38 LPA", "Python,Go,AWS,Kubernetes,Terraform,Docker,Prometheus,Grafana", "Ensure 99.99% uptime for Jira, Confluence, and Bitbucket serving millions of development teams globally."),
    
    # ── AI/ML Focused Companies ─────────────────────────────
    ("AI Research Scientist", "Google DeepMind India", "Bangalore", "Full-time", "35-60 LPA", "Python,PyTorch,TensorFlow,Deep Learning,NLP,Computer Vision,Mathematics,Research", "Conduct fundamental AI research on large language models, multimodal AI, and reinforcement learning."),
    ("ML Platform Engineer", "Walmart Global Tech India", "Bangalore", "Full-time", "18-32 LPA", "Python,Spark,Kubernetes,TensorFlow,SQL,Airflow,AWS,Docker", "Build ML infrastructure serving Walmart's recommendation, pricing, and supply chain optimization models at massive scale."),
    ("NLP Engineer", "Krutrim AI", "Bangalore", "Full-time", "18-35 LPA", "Python,PyTorch,NLP,Transformers,Deep Learning,CUDA,Linux,Hindi NLP", "Build India's own large language model. Develop multilingual NLP capabilities for 22 Indian languages."),
    ("Computer Vision Engineer", "Ather Energy", "Bangalore", "Full-time", "14-26 LPA", "Python,Computer Vision,Deep Learning,TensorFlow,C++,OpenCV,Edge AI", "Develop autonomous driving and ADAS features for India's leading electric scooter. Build perception and object detection systems."),
    ("Data Scientist", "Fractal Analytics", "Mumbai", "Full-time", "10-22 LPA", "Python,Machine Learning,SQL,R,Deep Learning,NLP,Spark,Tableau", "Build AI solutions for Fortune 500 clients in CPG, insurance, healthcare, and financial services."),
    ("AI Engineer", "MuSigma", "Bangalore", "Full-time", "6-14 LPA", "Python,Machine Learning,SQL,Statistics,R,Tableau,Deep Learning", "Develop decision science solutions and predictive analytics for global enterprises."),
    
    # ── Semiconductor & Hardware ─────────────────────────────
    ("Embedded Engineer", "Bosch India", "Bangalore", "Full-time", "8-18 LPA", "C,C++,Embedded Systems,RTOS,Python,CAN,Automotive,Linux", "Develop embedded software for automotive ECUs, ADAS, and IoT products at Bosch's largest R&D center outside Germany."),
    ("ASIC Design Engineer", "AMD India", "Hyderabad", "Full-time", "14-28 LPA", "Verilog,SystemVerilog,VLSI,Python,RTL Design,UVM,FPGA", "Design next-generation GPU and CPU architectures. Perform RTL design and verification for AMD Ryzen and Radeon processors."),
    ("Firmware Engineer", "Texas Instruments India", "Bangalore", "Full-time", "10-22 LPA", "C,C++,Embedded Systems,RTOS,ARM,Python,DSP,Linux", "Develop firmware for analog and embedded processing chips used in automotive, industrial, and consumer electronics."),
    
    # ── Cybersecurity ───────────────────────────────────────
    ("Security Analyst", "CrowdStrike India", "Pune", "Full-time", "12-22 LPA", "Python,SIEM,Threat Intelligence,Linux,Networking,Cloud Security,Malware Analysis", "Analyze cyber threats and develop detection rules. Protect enterprise clients from advanced persistent threats."),
    ("Cybersecurity Engineer", "Tata Communications", "Mumbai", "Full-time", "8-16 LPA", "Python,Linux,Networking,Firewall,SIEM,Cloud Security,Penetration Testing", "Build managed security services for enterprise clients. Implement SOC operations and incident response."),
    
    # ── Data & Analytics ────────────────────────────────────
    ("Data Engineer", "Cloudera India", "Bangalore", "Full-time", "14-26 LPA", "Python,Spark,Hadoop,SQL,Kafka,Airflow,AWS,Java", "Build enterprise data platforms. Develop next-generation data lake and data warehouse solutions on hybrid cloud."),
    ("Analytics Engineer", "ThoughtSpot India", "Hyderabad", "Full-time", "14-26 LPA", "SQL,Python,Snowflake,dbt,Spark,AWS,Data Modeling,Tableau", "Build AI-powered analytics search engine. Develop natural language query processing and data visualization features."),
    ("Business Intelligence Developer", "Mu Sigma", "Bangalore", "Full-time", "5-12 LPA", "SQL,Python,Tableau,Power BI,Excel,Statistics,R,ETL", "Build BI dashboards and reporting solutions for Fortune 500 clients across retail, banking, and pharma."),
    
    # ── Blockchain & Web3 ───────────────────────────────────
    ("Blockchain Developer", "Polygon (Matic)", "Bangalore", "Remote", "20-40 LPA", "Solidity,Rust,Go,Python,Ethereum,Web3,Smart Contracts,ZK Proofs", "Build Layer 2 scaling solutions for Ethereum. Develop zero-knowledge proof systems and blockchain infrastructure."),
    ("Smart Contract Engineer", "CoinDCX", "Mumbai", "Full-time", "14-28 LPA", "Solidity,JavaScript,Python,Web3.js,Ethereum,DeFi,Node.js,React", "Build DeFi protocols and trading infrastructure for India's largest cryptocurrency exchange."),
    
    # ── More Diverse Roles ──────────────────────────────────
    ("Technical Writer", "Atlassian India", "Bangalore", "Full-time", "10-18 LPA", "Technical Writing,Markdown,Git,API Documentation,DITA,HTML,JavaScript", "Create developer documentation for Jira, Confluence, and Bitbucket. Write API guides, tutorials, and best practices."),
    ("QA Engineer", "Freshworks", "Chennai", "Full-time", "6-14 LPA", "Selenium,Python,Java,Postman,API Testing,SQL,Jenkins,JIRA", "Design and execute test strategies for Freshworks SaaS products. Build automated test frameworks and ensure product quality."),
    ("UI/UX Designer", "Swiggy", "Bangalore", "Full-time", "12-24 LPA", "Figma,Sketch,Adobe XD,Prototyping,User Research,CSS,HTML,Design Systems", "Design intuitive food ordering and delivery experiences for 50M+ users. Conduct user research and A/B testing."),
    ("Product Manager", "Razorpay", "Bangalore", "Full-time", "18-35 LPA", "Product Strategy,SQL,Analytics,Agile,A/B Testing,User Research,Roadmapping", "Define product strategy for payment gateway and banking products. Drive growth for 8M+ businesses on the platform."),
    ("Engineering Manager", "Flipkart", "Bangalore", "Full-time", "30-50 LPA", "Java,System Design,Microservices,Leadership,AWS,Agile,Architecture", "Lead a team of 15+ engineers building Flipkart's supply chain platform. Drive technical strategy and team growth."),
    ("Database Administrator", "Tata Consultancy Services", "Chennai", "Full-time", "6-14 LPA", "Oracle,MySQL,PostgreSQL,SQL Server,MongoDB,AWS RDS,Performance Tuning,Backup", "Manage enterprise databases for banking and insurance clients. Optimize performance, ensure high availability, and implement disaster recovery."),
    ("Scrum Master", "Capgemini India", "Pune", "Full-time", "8-16 LPA", "Agile,Scrum,JIRA,Kanban,SAFe,Confluence,Leadership,Stakeholder Management", "Facilitate agile ceremonies and drive continuous improvement across cross-functional engineering teams."),
    ("Network Administrator", "Wipro", "Hyderabad", "Full-time", "5-10 LPA", "Cisco,Networking,Linux,AWS,Firewall,Monitoring,Python,Ansible", "Manage enterprise network infrastructure for global clients. Implement SD-WAN and cloud networking solutions."),
    ("Technical Support Engineer", "Zendesk India", "Bangalore", "Full-time", "6-12 LPA", "Python,SQL,REST APIs,Troubleshooting,Linux,Networking,JIRA,Communication", "Provide technical support for Zendesk's customer service platform. Debug API integrations and help enterprise clients."),
    ("Solutions Architect", "AWS India", "Mumbai", "Full-time", "22-40 LPA", "AWS,Python,Terraform,Kubernetes,Serverless,System Design,CloudFormation,Docker", "Help enterprises migrate to AWS cloud. Design scalable, fault-tolerant architectures for mission-critical workloads."),

    # ── Aerospace & Defence Tech ──────────────────────────────
    ("Software Engineer", "ISRO", "Bangalore", "Full-time", "8-16 LPA", "C,C++,Python,Linux,Embedded Systems,RTOS,Simulation,MATLAB", "Develop mission-critical software for India's space launch vehicles and satellite systems. Work on telemetry, guidance, and navigation systems."),
    ("Systems Engineer", "HAL (Hindustan Aeronautics)", "Bangalore", "Full-time", "7-14 LPA", "C,C++,MATLAB,Simulink,Embedded,Avionics,RTOS,DO-178C", "Design avionics software for fighter jets, helicopters, and UAVs. Ensure airworthiness compliance and real-time system safety."),
    ("Aerospace Software Engineer", "DRDO", "Hyderabad", "Full-time", "7-15 LPA", "C,C++,Python,Embedded Systems,Signal Processing,MATLAB,Linux", "Build defence electronics and missile guidance software. Contribute to India's strategic technology programs."),
    ("Software Developer", "Safran Engineering India", "Bangalore", "Full-time", "10-20 LPA", "C,C++,Python,Embedded,Avionics,DO-178,ARINC,MIL-STD", "Develop embedded avionics software for commercial aircraft landing gear and nacelle systems."),
    ("Embedded Engineer", "Honeywell India", "Hyderabad", "Full-time", "9-18 LPA", "C,C++,Python,Embedded,RTOS,Industrial IoT,Linux,Networking", "Build industrial automation and building management software for Honeywell's global product lines."),

    # ── Electric Vehicles & CleanTech ─────────────────────────
    ("Embedded Software Engineer", "Ola Electric", "Bangalore", "Full-time", "12-24 LPA", "C,C++,Python,RTOS,CAN,LIN,BMS,Embedded Linux", "Develop embedded software for Ola's electric scooters — battery management, motor control, and OTA update systems."),
    ("Battery Engineer", "Tata Motors EV", "Pune", "Full-time", "10-20 LPA", "Python,MATLAB,Simulink,BMS,CAN,Battery Chemistry,C,C++", "Design and test battery management systems for Nexon EV and upcoming EV platforms."),
    ("Software Engineer", "Revolt Motors", "Gurgaon", "Full-time", "8-16 LPA", "Python,IoT,AWS,React,Node.js,CAN,Embedded,Mobile", "Build connected vehicle platform and mobile app features for Revolt's electric motorcycle ecosystem."),
    ("Power Electronics Engineer", "Greaves Electric", "Pune", "Full-time", "8-16 LPA", "C,C++,Python,Power Electronics,MATLAB,Motor Control,CAN,Embedded", "Develop motor controllers and charging systems for Ampere electric scooters."),
    ("Data Engineer", "ReNew Power", "Gurgaon", "Full-time", "10-20 LPA", "Python,Spark,SQL,AWS,Airflow,IoT,Kafka,Tableau", "Build data platforms for India's largest renewable energy company. Monitor 10+ GW of wind and solar assets in real time."),

    # ── Pharmaceutical & BioTech ──────────────────────────────
    ("Bioinformatics Engineer", "Dr. Reddy's Laboratories", "Hyderabad", "Full-time", "8-16 LPA", "Python,R,Bioinformatics,Machine Learning,SQL,Genomics,Biopython", "Analyze genomic and proteomic data for drug discovery. Build computational pipelines for clinical trial data processing."),
    ("Data Scientist", "Sun Pharma", "Mumbai", "Full-time", "8-18 LPA", "Python,R,Machine Learning,SQL,Statistics,SAS,Clinical Data,Tableau", "Build predictive models for drug demand forecasting, clinical outcome analysis, and pharmacovigilance."),
    ("Software Engineer", "Cipla", "Mumbai", "Full-time", "7-15 LPA", "Python,Java,SQL,AWS,SAP,ERP,REST APIs,Data Analytics", "Develop pharmaceutical manufacturing execution systems and quality management software."),
    ("ML Engineer", "Sehat Sathi / MedGenome", "Bangalore", "Full-time", "12-22 LPA", "Python,Machine Learning,Genomics,Deep Learning,NLP,R,AWS,Docker", "Build AI models for rare disease diagnosis and genomic variant interpretation."),

    # ── Government Tech & Public Sector ──────────────────────
    ("Software Engineer", "NIC (National Informatics Centre)", "Delhi", "Full-time", "8-14 LPA", "Java,Python,Spring Boot,PostgreSQL,Linux,REST APIs,Docker", "Build e-governance portals and digital public services for central government ministries."),
    ("Backend Developer", "NPCI (UPI)", "Mumbai", "Full-time", "10-20 LPA", "Java,Spring Boot,MySQL,Redis,Kafka,AWS,Security,Microservices", "Build payment systems for UPI, IMPS, and RuPay handling billions of transactions for 1.4 billion Indians."),
    ("Data Engineer", "UIDAI (Aadhaar)", "Bangalore", "Full-time", "8-16 LPA", "Python,Hadoop,Spark,SQL,Biometrics,Security,AWS,ETL", "Build identity authentication infrastructure serving 1.3B Aadhaar holders for biometric and OTP verification."),
    ("Cloud Engineer", "C-DAC India", "Pune", "Full-time", "6-12 LPA", "Python,Linux,HPC,Kubernetes,AWS,Supercomputing,CUDA,MPI", "Build national high-performance computing infrastructure. Develop Param supercomputer applications and cloud services."),

    # ── Retail & D2C Tech ─────────────────────────────────────
    ("Backend Engineer", "Reliance Retail", "Mumbai", "Full-time", "12-22 LPA", "Java,Python,Microservices,Kafka,Redis,MySQL,AWS,Docker", "Build omnichannel retail platform integrating JioMart, Reliance Digital, and Smart Bazaar for India's largest retailer."),
    ("Full Stack Developer", "Decathlon India", "Bangalore", "Full-time", "8-16 LPA", "React,Node.js,Python,PostgreSQL,AWS,Docker,TypeScript,REST APIs", "Build e-commerce and store management systems for Decathlon India's retail and online sports channels."),
    ("Data Scientist", "Mamaearth", "Gurgaon", "Full-time", "10-20 LPA", "Python,Machine Learning,SQL,Tableau,A/B Testing,Pandas,Statistics", "Build customer lifetime value, churn prediction, and demand forecasting models for India's leading D2C beauty brand."),
    ("Software Engineer", "boAt Lifestyle", "Delhi", "Full-time", "8-16 LPA", "React,Node.js,Python,MongoDB,AWS,Shopify,REST APIs,Docker", "Build D2C e-commerce platform and IoT product connectivity for India's #1 hearables brand."),

    # ── HR Tech & Recruitment ─────────────────────────────────
    ("Backend Engineer", "Darwinbox", "Hyderabad", "Full-time", "12-22 LPA", "Python,Django,PostgreSQL,Redis,Celery,AWS,Docker,REST APIs", "Build next-generation HR software for 700+ enterprises. Develop payroll, performance management, and workforce analytics."),
    ("ML Engineer", "iimjobs.com / HackerEarth", "Bangalore", "Full-time", "10-20 LPA", "Python,Machine Learning,NLP,SQL,AWS,Docker,Recommendation Systems", "Build AI-powered job matching and technical assessment platforms used by 7000+ companies globally."),
    ("Product Engineer", "Keka HR", "Hyderabad", "Full-time", "8-16 LPA", "React,Node.js,Python,PostgreSQL,AWS,TypeScript,REST APIs,Docker", "Build modern HRMS and payroll solutions for SMBs. Develop attendance, leave management, and compliance features."),
    ("Full Stack Developer", "SpotDraft", "Delhi", "Full-time", "12-24 LPA", "React,Node.js,Python,PostgreSQL,AWS,NLP,TypeScript,Docker", "Build AI-powered contract lifecycle management platform. Develop document parsing and legal workflow automation."),

    # ── PropTech & Real Estate ────────────────────────────────
    ("Software Engineer", "NoBroker", "Bangalore", "Full-time", "10-20 LPA", "Python,Django,React,PostgreSQL,Redis,AWS,Elasticsearch,Docker", "Build India's largest proptech platform eliminating broker commissions. Develop property listing, rental agreements, and home services."),
    ("Backend Developer", "99acres (Info Edge)", "Noida", "Full-time", "8-16 LPA", "Java,Spring Boot,MySQL,Elasticsearch,Redis,AWS,Kafka,Microservices", "Build real estate marketplace features for property search, listing management, and lead generation."),
    ("Data Scientist", "Square Yards", "Gurgaon", "Full-time", "8-16 LPA", "Python,Machine Learning,SQL,Statistics,Tableau,Real Estate Analytics", "Build property price prediction and investment recommendation models using location intelligence and market data."),

    # ── AgriTech ──────────────────────────────────────────────
    ("Backend Engineer", "DeHaat", "Patna", "Full-time", "8-16 LPA", "Python,Django,PostgreSQL,Redis,AWS,Docker,REST APIs,Mobile", "Build agri-commerce platform connecting 900K+ farmers with inputs, advisory, and market linkages across 12 Indian states."),
    ("ML Engineer", "Cropin Technology", "Bangalore", "Full-time", "10-20 LPA", "Python,Machine Learning,Computer Vision,Satellite Imagery,GIS,Deep Learning,AWS", "Build AI models for crop disease detection, yield prediction, and farm advisory using satellite and drone imagery."),
    ("Full Stack Developer", "AgroStar", "Ahmedabad", "Full-time", "8-16 LPA", "React,Node.js,Python,MongoDB,AWS,TypeScript,REST APIs,Mobile", "Build agri-input e-commerce and advisory platform serving 6M+ farmers across India."),

    # ── InsurTech ─────────────────────────────────────────────
    ("Data Scientist", "Acko Insurance", "Bangalore", "Full-time", "14-26 LPA", "Python,Machine Learning,SQL,Statistics,R,Deep Learning,Actuarial Science", "Build underwriting, pricing, and fraud detection models for India's digital-first insurance company."),
    ("Backend Engineer", "Digit Insurance", "Bangalore", "Full-time", "12-22 LPA", "Java,Spring Boot,PostgreSQL,Redis,Kafka,AWS,Microservices,Docker", "Build insurance policy management and claims processing systems for India's fastest-growing general insurer."),
    ("ML Engineer", "Turtlemint", "Mumbai", "Full-time", "10-20 LPA", "Python,Machine Learning,NLP,SQL,AWS,Docker,Recommendation Systems", "Build AI-powered insurance advisory and comparison engines. Develop natural language document processing for claims."),

    # ── Space Tech ────────────────────────────────────────────
    ("Software Engineer", "Skyroot Aerospace", "Hyderabad", "Full-time", "10-20 LPA", "C,C++,Python,Embedded,RTOS,GNC,Simulation,Linux", "Build flight software for Vikram rockets — India's first private orbital launch vehicles. Develop guidance navigation and control systems."),
    ("Systems Engineer", "Agnikul Cosmos", "Chennai", "Full-time", "8-18 LPA", "Python,MATLAB,C++,Embedded,GNC,Simulation,Systems Engineering", "Design and develop launch vehicle avionics for Agnibaan — the world's first single-piece 3D-printed rocket engine."),
    ("Data Engineer", "Pixxel Space", "Bangalore", "Full-time", "10-18 LPA", "Python,AWS,Satellite Imagery,GIS,Spark,PostgreSQL,Computer Vision,Rasterio", "Build satellite data processing pipelines for Pixxel's hyperspectral imaging constellation."),

    # ── Media, Entertainment & Content ────────────────────────
    ("Backend Engineer", "Zee5", "Mumbai", "Full-time", "12-22 LPA", "Java,Python,AWS,Kafka,Redis,Microservices,CDN,Elasticsearch", "Build OTT streaming infrastructure for Zee5 serving 100M+ viewers. Develop content delivery, DRM, and recommendation systems."),
    ("Software Engineer", "Times Internet", "Noida", "Full-time", "10-20 LPA", "Java,Python,React,AWS,Kafka,Redis,Microservices,Elasticsearch", "Build digital news and entertainment platforms for Times of India, Economic Times, and Cricbuzz."),
    ("ML Engineer", "Dailyhunt (VerSe Innovation)", "Bangalore", "Full-time", "14-26 LPA", "Python,NLP,Deep Learning,Recommendation Systems,SQL,AWS,Multilingual AI", "Build personalized news recommendation and regional language NLP models for 350M+ Indian users."),
    ("Data Scientist", "InMobi", "Bangalore", "Full-time", "14-26 LPA", "Python,Machine Learning,SQL,Spark,Ad Tech,Deep Learning,A/B Testing,AWS", "Build programmatic advertising models for InMobi's mobile ad platform reaching 2B+ devices globally."),

    # ── Supply Chain & Manufacturing Tech ─────────────────────
    ("Software Engineer", "Juspay", "Bangalore", "Full-time", "12-22 LPA", "Haskell,PureScript,Java,Python,PostgreSQL,Redis,AWS,Payments", "Build payment orchestration infrastructure processing 50M+ transactions daily for Amazon, Flipkart, and Jio."),
    ("Data Engineer", "Moglix", "Noida", "Full-time", "10-18 LPA", "Python,Spark,SQL,AWS,Airflow,Kafka,Tableau,ETL", "Build B2B manufacturing commerce data platform serving 500+ large manufacturers and 5000+ suppliers."),
    ("Backend Developer", "OfBusiness", "Gurgaon", "Full-time", "12-22 LPA", "Java,Python,Spring Boot,MySQL,Redis,Kafka,AWS,Microservices", "Build B2B industrial commodity marketplace handling ₹5000+ crore GMV monthly."),

    # ── Consulting & IT Services (More) ───────────────────────
    ("Software Engineer", "Persistent Systems", "Pune", "Full-time", "8-16 LPA", "Java,Python,React,AWS,Docker,Spring Boot,Microservices,SQL", "Build enterprise software solutions for healthcare, life sciences, and BFSI clients across North America and Europe."),
    ("Data Analyst", "Coforge (Niit Tech)", "Noida", "Full-time", "6-12 LPA", "Python,SQL,Power BI,Tableau,Excel,ETL,Statistics,Azure", "Deliver data analytics and BI solutions for travel, BFS, and insurance clients globally."),
    ("Cloud Consultant", "Hexaware Technologies", "Mumbai", "Full-time", "8-16 LPA", "AWS,Azure,Python,Terraform,Docker,Kubernetes,DevOps,Jenkins", "Lead cloud migration and modernization programs for Fortune 500 clients."),
    ("DevOps Engineer", "Birlasoft", "Noida", "Full-time", "7-14 LPA", "AWS,Azure,Kubernetes,Docker,Jenkins,Terraform,Python,Ansible", "Build DevOps pipelines and cloud infrastructure for manufacturing and BFSI sector clients."),

    # ── Social Impact & NGO Tech ──────────────────────────────
    ("Full Stack Developer", "iSPIRT Foundation", "Bangalore", "Full-time", "8-16 LPA", "Python,React,Node.js,PostgreSQL,AWS,Docker,REST APIs,Open Source", "Build India's digital public infrastructure including Account Aggregator, ONDC, and Beckn Protocol."),
    ("Software Engineer", "EkStep Foundation", "Bangalore", "Full-time", "8-16 LPA", "Java,Python,Node.js,React,AWS,Kubernetes,Open Source,EdTech", "Develop Diksha — India's national digital education platform used by 200M+ students and 3M+ teachers."),

    # ── Automotive Tech ───────────────────────────────────────
    ("Software Engineer", "Mahindra Tech", "Pune", "Full-time", "8-16 LPA", "C,C++,Python,Automotive,AUTOSAR,CAN,Embedded,MISRA C", "Build advanced driver assistance systems and connected vehicle software for Mahindra electric vehicles."),
    ("ADAS Engineer", "Tata Elxsi", "Bangalore", "Full-time", "10-20 LPA", "Python,C++,Computer Vision,Deep Learning,ROS,Sensor Fusion,Autonomous Driving", "Design perception and planning algorithms for autonomous driving platforms. Develop LIDAR, camera, and radar fusion systems."),
    ("Embedded Developer", "Maruti Suzuki India", "Gurgaon", "Full-time", "7-14 LPA", "C,C++,AUTOSAR,CAN,Python,Embedded Linux,QNX,Diagnostics", "Develop infotainment, telematics, and OBD diagnostic software for Maruti's next-generation connected vehicles."),

    # ── International Companies with Large India Teams ─────────
    ("Software Engineer", "Uber India", "Hyderabad", "Full-time", "22-40 LPA", "Go,Python,Java,Kafka,MySQL,Kubernetes,AWS,Distributed Systems", "Build global ride-sharing and Uber Eats systems. Work on routing, pricing, and marketplace platforms at massive scale."),
    ("Backend Engineer", "LinkedIn India", "Bangalore", "Full-time", "24-45 LPA", "Java,Scala,Python,Kafka,Espresso,Hadoop,Spark,Kubernetes", "Build professional networking features used by 950M+ members. Work on feed, search, and recruiter intelligence."),
    ("Software Engineer", "Adobe India", "Noida", "Full-time", "20-38 LPA", "C++,Java,Python,React,AWS,Machine Learning,Computer Vision,Creative AI", "Build generative AI features for Adobe Firefly, Photoshop, and Premiere Pro. Work on Sensei AI platform."),
    ("Data Scientist", "Spotify India", "Mumbai", "Full-time", "20-35 LPA", "Python,Machine Learning,Spark,SQL,A/B Testing,Recommendation Systems,Scala", "Build personalized music recommendation models for 600M+ users. Develop Discover Weekly and Wrapped features."),
    ("SDE II", "Netflix India", "Mumbai", "Full-time", "25-45 LPA", "Java,Python,AWS,Kafka,Microservices,React,System Design,Chaos Engineering", "Build streaming infrastructure handling 250M+ subscribers. Develop content delivery, A/B testing, and recommendation systems."),
]

def seed_jobs():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Clear existing jobs
    cursor.execute("DELETE FROM jobs")
    
    # Insert all real jobs
    for title, company, location, job_type, salary, skills, description in REAL_JOBS:
        cursor.execute(
            "INSERT INTO jobs (title, company, location, type, salary, skills, description, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (title, company, location, job_type, salary, skills, description, "Active")
        )
    
    conn.commit()
    total = cursor.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    print(f"\n{'='*60}")
    print(f"  Successfully inserted {total} REAL company jobs!")
    print(f"{'='*60}")
    
    # Show company count
    companies = cursor.execute("SELECT COUNT(DISTINCT company) FROM jobs").fetchone()[0]
    print(f"  Unique companies: {companies}")
    
    # Show top companies
    print(f"\n  Sample companies:")
    for row in cursor.execute("SELECT DISTINCT company FROM jobs ORDER BY company LIMIT 20").fetchall():
        print(f"    • {row[0]}")
    print(f"    ... and {companies - 20} more!")
    
    conn.close()

if __name__ == "__main__":
    seed_jobs()
