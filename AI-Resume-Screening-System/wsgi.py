# ============================================================
#  TalentSync — Production WSGI Entry Point
#  Exports the application instance for Gunicorn / uWSGI.
# ============================================================

import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "0.0.0.0")
    app.run(host=host, port=port)
