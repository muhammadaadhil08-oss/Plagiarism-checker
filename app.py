import sys
import os

# Add the 'backend' folder to the python path so the backend app can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app import app

if __name__ == "__main__":
    # Start the Flask development server
    app.run(debug=True, port=8000)
