FROM python:3.11-slim

WORKDIR /app

# Install TeX Live and other dependencies
RUN apt-get update && apt-get install -y \
    texlive \
    texlive-latex-extra \
    texlive-fonts-recommended \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p data resources

# Copy application code (excluding requirements.txt for now)
COPY . .

# Install dependencies directly (avoiding pylatex installation issues)
RUN pip install --no-cache-dir flask==2.3.3 requests==2.31.0 tenacity==8.2.3 Jinja2==3.1.2 Werkzeug==2.3.7 click==8.1.7

# Fix PyLaTeX installation - patch and install from source
RUN cd /tmp && \
    curl -L https://github.com/JelteF/PyLaTeX/archive/refs/tags/v1.4.1.tar.gz -o pylatex.tar.gz && \
    tar xzf pylatex.tar.gz && \
    cd PyLaTeX-1.4.1 && \
    # Replace SafeConfigParser with ConfigParser
    sed -i 's/SafeConfigParser/ConfigParser/g' versioneer.py && \
    pip install . && \
    cd /app && \
    rm -rf /tmp/PyLaTeX-1.4.1 /tmp/pylatex.tar.gz

# Update Ollama URL in the service file
RUN sed -i 's/base_url="http:\/\/localhost:11434"/base_url=os.environ.get("OLLAMA_BASE_URL", "http:\/\/localhost:11434")/g' pylaform/services/ai_service.py && \
    sed -i 's/import json/import json\nimport os/g' pylaform/services/ai_service.py && \
    sed -i 's/self.model = "llama3.2:1b"/self.model = os.environ.get("OLLAMA_MODEL", "llama3.2:1b")/g' pylaform/services/ai_service.py

# Expose Flask port
EXPOSE 5000

# Default command (will be overridden by docker-compose)
CMD ["python", "app.py"]