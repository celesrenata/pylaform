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

# Copy application code
COPY . .

# Install dependencies directly (avoiding pylatex installation issues)
# Added flask-cors to the pip install command
RUN pip install --no-cache-dir flask==2.3.3 requests==2.31.0 tenacity==8.2.3 Jinja2==3.1.2 Werkzeug==2.3.7 click==8.1.7 flask-cors==4.0.0

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

# Use pre-created modified files to avoid shell quoting issues
COPY ./pylaform/resources/modified_ai_service.py /tmp/
COPY ./pylaform/resources/modified_app.py /tmp/
COPY ./pylaform/resources/start.sh /tmp/

# Now install them with simple copy commands
RUN cp /tmp/modified_ai_service.py /app/pylaform/services/ai_service.py && \
    cp /tmp/modified_app.py /app/app.py && \
    cp /tmp/start.sh /app/start.sh && \
    chmod +x /app/start.sh

# Expose Flask port
EXPOSE 5000

# Set default environment variables
ENV ENABLE_AI=true \
    OLLAMA_BASE_URL=http://ollama:11434 \
    OLLAMA_MODEL=llama3.2:1b \
    DOWNLOAD_MODEL=true

# Default command
ENTRYPOINT ["/app/start.sh"]