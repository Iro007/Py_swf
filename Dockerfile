FROM python:3.11-slim

# Install minimal packages for running tests; GUI in container requires additional X11 setup
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1-mesa-glx \
    libx11-6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# Default: run tests
CMD ["python", "tests/test_swf.py"]
