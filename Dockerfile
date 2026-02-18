FROM python:3.9-slim

WORKDIR /app

# Install system dependencies if needed (e.g., for building some python libs)
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# We don't strictly need to COPY . . if using volumes for dev, 
# but it's good practice for the image to be functional standalone.
COPY . .

CMD ["flask", "run", "--host=0.0.0.0", "--port=5001"]
