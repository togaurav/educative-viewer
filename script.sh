#!/bin/bash

python3 -m venv venv

# Navigate to your project directory
cd /Users/om/Documents/educative-viewer || exit

# Activate the virtual environment (adjust if venv is in a different location)
source venv/bin/activate

pip install -r requirements.txt

cd ..
# Export required environment variables
export course_dir="/Users/om/Grokking"
export FLASK_APP="educative-viewer"
export authtoken="112122343ff"
export downloadtoken="112122343ff"

# Run Flask app
flask run --host=0.0.0.0 --port=5001

# Deactivate virtual environment when Flask server stops
deactivate
