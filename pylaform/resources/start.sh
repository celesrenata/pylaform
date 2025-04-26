#!/bin/bash

# Get environment variables with defaults
MODEL=${OLLAMA_MODEL:-"llama3.2:1b"}
BASE_URL=${OLLAMA_BASE_URL:-"http://ollama:11434"}
DOWNLOAD=${DOWNLOAD_MODEL:-"true"}

echo "Starting with model: $MODEL"
echo "Ollama URL: $BASE_URL"

# If download is enabled, try to download the model
if [ "$DOWNLOAD" = "true" ]; then
    echo "Checking if model $MODEL is available..."

    # Check if model exists
    MODEL_CHECK=$(curl -s "$BASE_URL/api/tags" | grep -o "\"name\":\"$MODEL\"" || echo "")

    if [ -z "$MODEL_CHECK" ]; then
        echo "Model $MODEL not found, initiating download..."
        curl -s -X POST "$BASE_URL/api/pull" -d "{\"name\":\"$MODEL\"}" > /dev/null &
        echo "Download initiated in background. App will start while model downloads."
    else
        echo "Model $MODEL already available."
    fi
fi

# Start the app
echo "Starting Flask application..."
python app.py