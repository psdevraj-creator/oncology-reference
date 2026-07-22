import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

app = create_app()
server = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
