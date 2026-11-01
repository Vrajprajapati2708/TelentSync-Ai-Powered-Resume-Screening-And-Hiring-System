"""
TalentSync Migration: Technical Quiz Gatekeeper (Step 8)
Creates `quiz_questions` and `quiz_attempts` tables and seeds initial technical question bank.
"""

import os
import sys
import json
import sqlite3

# Ensure app package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))


INITIAL_QUESTIONS = [
    # Python
    ("Python", "How does the Python Global Interpreter Lock (GIL) affect multithreading in CPython?",
     json.dumps(["It enables automatic thread pooling across CPU cores.", "It allows only one native thread to execute Python bytecode at a time.", "It replaces the garbage collector for reference counting.", "It prevents deadlocks across async event loops."]), 1, "intermediate"),
    ("Python", "What is the average time complexity of lookups in a Python dictionary?",
     json.dumps(["O(n)", "O(log n)", "O(1)", "O(n log n)"]), 2, "easy"),
    ("Python", "Which Python keyword transforms a standard function into a generator that yields values on demand?",
     json.dumps(["return", "yield", "async", "await"]), 1, "easy"),
    ("Python", "What does the @property decorator do in a Python class?",
     json.dumps(["Defines a static class method.", "Declares a private instance variable.", "Allows a method to be accessed like an attribute with getters/setters.", "Caches the return value permanently in memory."]), 2, "intermediate"),
    ("Python", "What is the primary difference between a list and a tuple in Python?",
     json.dumps(["Lists are immutable; tuples are mutable.", "Lists are mutable; tuples are immutable.", "Tuples allow faster dictionary key lookups than integers.", "Lists cannot contain mixed data types."]), 1, "easy"),

    # Docker
    ("Docker", "What is the primary architectural advantage of a multi-stage Docker build?",
     json.dumps(["It reduces final production image size by leaving build tools out of the final layer.", "It runs containers across multiple operating systems simultaneously.", "It allows multiple entrypoints inside a single container.", "It bypasses layer caching during development."]), 0, "intermediate"),
    ("Docker", "What happens when a Docker container is deleted if no volumes were mounted?",
     json.dumps(["The data is persisted in the image cache.", "The writable layer and container state are permanently lost.", "The data is exported to /var/log/docker automatically.", "The data is preserved in the Docker daemon memory."]), 1, "easy"),
    ("Docker", "In a Dockerfile, what is the key difference between CMD and ENTRYPOINT?",
     json.dumps(["CMD sets the container host; ENTRYPOINT sets the port.", "ENTRYPOINT defines the default executable; CMD provides default arguments that can be overridden.", "CMD runs during build time; ENTRYPOINT runs at runtime.", "There is no difference; they are aliases."]), 1, "intermediate"),
    ("Docker", "Which Docker command downloads an image from a remote registry without starting a container?",
     json.dumps(["docker run", "docker pull", "docker push", "docker start"]), 1, "easy"),
    ("Docker", "What is the purpose of the .dockerignore file?",
     json.dumps(["To ignore containers during system prune.", "To exclude specified files and directories from the build context sent to the Docker daemon.", "To silence Docker warning logs.", "To prevent images from being published to Docker Hub."]), 1, "easy"),

    # Kubernetes
    ("Kubernetes", "What is the smallest deployable computing unit in Kubernetes?",
     json.dumps(["Container", "Pod", "Service", "Node"]), 1, "easy"),
    ("Kubernetes", "Which Kubernetes resource provides a stable virtual IP address and load balances traffic across a dynamic set of Pods?",
     json.dumps(["Deployment", "Service", "ConfigMap", "Ingress"]), 1, "easy"),
    ("Kubernetes", "What is the purpose of a Readiness Probe in a Kubernetes Pod?",
     json.dumps(["It restarts the container if it crashes.", "It determines if the container is ready to accept incoming network traffic.", "It measures container disk utilization.", "It allocates cluster memory dynamically."]), 1, "intermediate"),
    ("Kubernetes", "Which controller should be used in Kubernetes when workloads require persistent network identities and stable ordered storage?",
     json.dumps(["ReplicaSet", "DaemonSet", "StatefulSet", "Job"]), 2, "intermediate"),
    ("Kubernetes", "What component on a Kubernetes worker node is responsible for maintaining network rules and IP forwarding for Services?",
     json.dumps(["kubelet", "kube-proxy", "kube-scheduler", "etcd"]), 1, "intermediate"),

    # AWS
    ("AWS", "What is the difference between an AWS IAM Role and an IAM User?",
     json.dumps(["IAM Users have permissions; IAM Roles have no permissions.", "An IAM User is tied to a person/identity with permanent credentials; an IAM Role is assumed temporarily by services or identities.", "IAM Roles only apply to EC2 instances, not Lambda.", "IAM Users cannot access the AWS Management Console."]), 1, "intermediate"),
    ("AWS", "Which S3 storage class offers the lowest cost for long-term data archiving with retrieval times of several hours?",
     json.dumps(["S3 Standard", "S3 Intelligent-Tiering", "S3 Glacier Flexible Retrieval", "S3 One Zone-IA"]), 2, "easy"),
    ("AWS", "What is the primary function of an AWS VPC NAT Gateway?",
     json.dumps(["To route inbound traffic from the internet to private instances.", "To allow instances in a private subnet to connect outbound to the internet while preventing inbound connections.", "To provide private DNS resolution across VPCs.", "To encrypt traffic between S3 and EC2."]), 1, "intermediate"),
    ("AWS", "What is the maximum execution duration for an AWS Lambda function?",
     json.dumps(["5 minutes", "15 minutes", "1 hour", "Unlimited"]), 1, "easy"),
    ("AWS", "Which AWS service is a managed, serverless NoSQL database that offers single-digit millisecond latency?",
     json.dumps(["Amazon RDS", "Amazon DynamoDB", "Amazon Redshift", "Amazon Aurora"]), 1, "easy"),

    # SQL / Database
    ("SQL", "What is the key difference between WHERE and HAVING clauses in SQL?",
     json.dumps(["WHERE filters rows before aggregation; HAVING filters groups after aggregation.", "WHERE is used for joins; HAVING is used for subqueries.", "HAVING is faster than WHERE on indexed columns.", "WHERE requires an aggregate function like SUM or COUNT."]), 0, "easy"),
    ("SQL", "Which index data structure is most commonly used in relational databases for range queries and equality lookups?",
     json.dumps(["Hash Table", "B-Tree", "Linked List", "Radix Tree"]), 1, "intermediate"),
    ("SQL", "What does the 'I' stand for in database ACID transaction properties?",
     json.dumps(["Immutability", "Indexing", "Isolation", "Idempotence"]), 2, "easy"),
    ("SQL", "What is a major consequence of an uncommitted transaction in Read Committed isolation level?",
     json.dumps(["Dirty reads are prevented; phantom reads may still occur.", "All reads are permanently blocked across the database.", "Deadlocks are mathematically impossible.", "Data is lost if the server loses power."]), 0, "intermediate"),
    ("SQL", "Which SQL JOIN returns all rows from the left table and matched rows from the right table?",
     json.dumps(["INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL OUTER JOIN"]), 1, "easy"),

    # Git
    ("Git", "What is the main difference between 'git merge' and 'git rebase'?",
     json.dumps(["Rebase creates a merge commit; merge does not.", "Rebase rewrites commit history by moving commits onto a new base commit; merge preserves original history with a merge commit.", "Merge deletes the source branch automatically.", "Rebase cannot be used with GitHub."]), 1, "intermediate"),
    ("Git", "What does a 'detached HEAD' state in Git mean?",
     json.dumps(["The Git repository is corrupted.", "HEAD points directly to a commit rather than to a named branch.", "The origin remote has been disconnected.", "The local working directory has uncommitted merge conflicts."]), 1, "intermediate"),
    ("Git", "Which Git command reverts a specific commit by creating a new inverse commit without rewriting history?",
     json.dumps(["git reset --hard", "git revert", "git checkout", "git clean"]), 1, "easy"),

    # Distributed Systems
    ("Distributed Systems", "According to the CAP theorem, which property must a distributed system sacrifice when a network partition occurs?",
     json.dumps(["Consistency or Availability", "Latency or Throughput", "Security or Scalability", "Persistence or Idempotence"]), 0, "intermediate"),
    ("Distributed Systems", "What is the primary purpose of the Circuit Breaker pattern in microservices?",
     json.dumps(["To balance database connections across nodes.", "To prevent cascading failures by failing fast when a downstream dependency is degraded.", "To encrypt traffic between services.", "To serialize JSON payloads into binary streams."]), 1, "intermediate"),
    ("Distributed Systems", "What does it mean for an API operation to be 'idempotent'?",
     json.dumps(["It executes within a single database transaction.", "Calling the operation multiple times with identical parameters produces the same result as a single call.", "It requires mutual TLS authentication.", "It caches the response permanently in Redis."]), 1, "intermediate"),
]


def run_migration(db_path: str):
    if not os.path.exists(db_path):
        print(f"[!] Database path does not exist: {db_path}")
        return

    print(f"[*] Running Technical Quiz Gatekeeper Migration on: {db_path}")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Create quiz_questions table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quiz_questions (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            skill          TEXT NOT NULL,
            question       TEXT NOT NULL,
            options        TEXT NOT NULL,
            correct_option INTEGER NOT NULL,
            difficulty     TEXT DEFAULT 'intermediate',
            created_at     TEXT DEFAULT (datetime('now'))
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_quiz_questions_skill ON quiz_questions(skill)")

    # 2. Create quiz_attempts table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            skill           TEXT NOT NULL,
            score           INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            correct_answers INTEGER NOT NULL,
            passed          INTEGER NOT NULL,
            attempted_at    TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user_skill ON quiz_attempts(user_id, skill)")

    # 3. Seed question bank
    existing_q_count = cur.execute("SELECT COUNT(*) FROM quiz_questions").fetchone()[0]
    seeded_count = 0
    if existing_q_count == 0:
        for sk, q, opts, correct, diff in INITIAL_QUESTIONS:
            cur.execute(
                """INSERT INTO quiz_questions (skill, question, options, correct_option, difficulty)
                   VALUES (?, ?, ?, ?, ?)""",
                (sk, q, opts, correct, diff)
            )
            seeded_count += 1

    conn.commit()
    conn.close()
    print(f"[+] Migration complete for {db_path}. Seeded {seeded_count} technical questions.")


if __name__ == '__main__':
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    db_file = os.path.join(base_dir, 'instance', 'talentsync.db')
    if not os.path.exists(db_file):
        db_file = os.path.join(base_dir, 'talentsync.db')

    run_migration(db_file)

    backup_db = os.path.join(base_dir, 'talentsync_backup_phase5.db')
    if os.path.exists(backup_db):
        run_migration(backup_db)
