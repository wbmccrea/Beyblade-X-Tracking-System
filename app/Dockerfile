# Use a Python base image
FROM python:3.11-slim-bullseye

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file FIRST
COPY requirements.txt .

# Install system dependencies if needed (e.g., for mysqlclient)
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies using requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code AFTER installing requirements
COPY . .

# Expose the port the app runs on
EXPOSE 5000

# Set the entrypoint for the container
CMD ["flask", "run", "--host=0.0.0.0"]