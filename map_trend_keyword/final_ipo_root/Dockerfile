# Use an official lightweight Python image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Install system dependencies, including Java
RUN apt-get update && apt-get install -y python3-venv python3-pip openjdk-17-jdk && rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME environment variable
ENV JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"
ENV PATH="$JAVA_HOME/bin:$PATH"

# Copy only requirements.txt to leverage Docker cache
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files into the container
COPY . /app

# Ensure the script has execution permissions
RUN chmod +x setup_and_run.sh

# Expose necessary ports for FastAPI and TorchServe
EXPOSE 8002

# Run the setup script when the container starts
CMD ["bash", "./setup_and_run.sh"]
