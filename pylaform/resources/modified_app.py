from flask_cors import CORS
from flask import Flask, render_template, request, send_from_directory, jsonify
import os
import requests
from pylaform.commands.db.query import Queries
from pylaform.commands.templateWorker import Worker
from pylaform.latex_templates import hybrid, onePage
from pylaform.utilities.commands import fatten, listify
from pylaform.services.ai_service import OllamaService

# Initialize the AI service
ai_service = OllamaService()

app = Flask(__name__,
            static_url_path="",
            static_folder="pylaform/static",
            template_folder="pylaform/templates")
CORS(app, origins="*", supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     methods=["GET", "POST", "OPTIONS"])


# Not currently used.
app.jinja_env.add_extension('jinja2.ext.do')

query = Queries()
worker = Worker()
uploads: str = os.path.join(app.root_path, 'data')


@app.route("/")
def landing():
    return render_template("landing.html", **fatten(query.get_identification()))

@app.route("/api/ai-status", methods=["GET"])
def ai_status():
    """Check if the Ollama service is available"""
    if not ai_service.ai_enabled:
        return jsonify({"status": "disabled", "message": "AI service is disabled. Set ENABLE_AI=true to enable."})
    try:
        # Simple health check
        response = requests.get(f"{ai_service.base_url}/api/tags")
        if response.status_code == 200:
            return jsonify({"status": "ok", "models": response.json().get("models", [])})
        else:
            return jsonify({"status": "error", "message": f"Ollama returned status code {response.status_code}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/information", methods=["GET", "POST"])
def information():
    if request.method == 'POST':
        worker.identification(request.form)
        query.purge_cache("identification")
    return render_template("information.html", **fatten(query.get_identification()))

@app.route("/api/improve-text", methods=["POST"])
def improve_text():
    """API endpoint to get AI improvements for resume text"""
    if not request.is_json:
        return jsonify({"error": "Expected JSON data"}), 400

    data = request.json
    text = data.get("text", "")
    improvement_type = data.get("type", "")

    if not text or not improvement_type:
        return jsonify({"error": "Missing required fields"}), 400

    if not ai_service.ai_enabled:
        return jsonify({"response": "AI improvements are currently disabled. Please enable the AI service or connect to an Ollama instance to use this feature.", "ai_disabled": True})

    result = ai_service.generate_improvement(text, improvement_type)

    if "error" in result:
        return jsonify(result), 500

    return jsonify(result)


@app.route("/api/network-test", methods=["GET"])
def network_test():
    """Test connectivity to the Ollama server and display diagnostic information"""
    try:
        # First, get the configured URL
        base_url = ai_service.base_url

        # Try pinging the server
        ping_url = f"{base_url}/api/health"
        ping_start = time.time()
        try:
            ping_response = requests.get(ping_url, timeout=5)
            ping_time = time.time() - ping_start
            ping_status = ping_response.status_code
            ping_success = ping_response.status_code == 200
        except Exception as e:
            ping_success = False
            ping_status = str(e)
            ping_time = time.time() - ping_start

        # Try getting model list
        models_url = f"{base_url}/api/tags"
        models_start = time.time()
        try:
            models_response = requests.get(models_url, timeout=5)
            models_time = time.time() - models_start
            models_status = models_response.status_code
            if models_response.status_code == 200:
                try:
                    models_data = models_response.json()
                    models_list = [model["name"] for model in models_data.get("models", [])]
                except:
                    models_list = ["Error parsing response"]
            else:
                models_list = []
        except Exception as e:
            models_status = str(e)
            models_time = time.time() - models_start
            models_list = []

        # Try DNS resolution (only works if Python has access to the Docker DNS)
        dns_result = None
        try:
            import socket
            ollama_host = base_url.split("://")[1].split(":")[0]
            dns_result = socket.gethostbyname(ollama_host)
        except Exception as e:
            dns_result = str(e)

        # Return all diagnostic information
        return jsonify({
            "ollama_config": {
                "base_url": base_url,
                "model": ai_service.model,
                "enabled": ai_service.ai_enabled
            },
            "ping_test": {
                "url": ping_url,
                "success": ping_success,
                "status": ping_status,
                "time_ms": round(ping_time * 1000, 2)
            },
            "models_test": {
                "url": models_url,
                "status": models_status,
                "time_ms": round(models_time * 1000, 2),
                "models": models_list
            },
            "dns_resolution": {
                "host": ollama_host,
                "result": dns_result
            },
            "environment": {
                "OLLAMA_BASE_URL": os.environ.get("OLLAMA_BASE_URL", "Not set"),
                "OLLAMA_MODEL": os.environ.get("OLLAMA_MODEL", "Not set"),
                "ENABLE_AI": os.environ.get("ENABLE_AI", "Not set")
            }
        })
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route("/api/download-model", methods=["POST"])
def download_model():
    """Download a specified Ollama model"""
    if not request.is_json:
        return jsonify({"error": "Expected JSON data"}), 400

    data = request.json
    model_name = data.get("model")

    if not model_name:
        return jsonify({"error": "Model name is required"}), 400

    try:
        # Call Ollama's pull API to download the model
        payload = {
            "name": model_name
        }

        print(f"Initiating download of model: {model_name}")

        # Make the request to Ollama's pull API
        response = requests.post(
            f"{ai_service.base_url}/api/pull",
            headers={"Content-Type": "application/json"},
            json=payload,
            stream=True  # Use streaming since model downloads can take time
        )

        # Check response code
        if response.status_code != 200:
            return jsonify({
                "error": f"Failed to start model download: {response.text}"
            }), 500

        # Since Ollama pulls are asynchronous, we can return success immediately
        return jsonify({
            "message": f"Model download initiated for {model_name}",
            "status": "downloading"
        })

    except Exception as e:
        print(f"Error downloading model: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": f"Error downloading model: {str(e)}"}), 500


@app.route("/api/model-status", methods=["GET"])
def model_status():
    """Check if specified model is available and its download status"""
    model_name = request.args.get("model")

    if not model_name:
        return jsonify({"error": "Model name is required"}), 400

    try:
        # Get the list of available models
        response = requests.get(f"{ai_service.base_url}/api/tags", timeout=5)

        if response.status_code != 200:
            return jsonify({
                "error": f"Failed to get model list: {response.text}",
                "status": "unknown"
            }), 500

        # Parse response to check if model exists
        models_data = response.json()
        available_models = [model["name"] for model in models_data.get("models", [])]

        # Check if model is being downloaded
        pull_response = requests.get(f"{ai_service.base_url}/api/show",
                                     params={"name": model_name},
                                     timeout=5)

        if pull_response.status_code == 200:
            pull_data = pull_response.json()
            # If model exists in the list of models
            if model_name in available_models:
                return jsonify({
                    "status": "available",
                    "model": model_name,
                    "details": pull_data
                })
            else:
                # Model might be downloading
                return jsonify({
                    "status": "downloading",
                    "model": model_name,
                    "details": pull_data
                })
        elif pull_response.status_code == 404:
            # Model is not available and not being downloaded
            return jsonify({
                "status": "not_available",
                "model": model_name
            })
        else:
            return jsonify({
                "status": "unknown",
                "model": model_name,
                "error": pull_response.text
            })

    except Exception as e:
        print(f"Error checking model status: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            "error": f"Error checking model status: {str(e)}",
            "status": "error"
        }), 500

@app.route("/docker-test", methods=["GET"])
def docker_test_page():
    """Test page specifically for Docker setup"""
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Docker Network Test</title>
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; max-width: 1200px; }
            pre { background: #f5f5f5; padding: 10px; border-radius: 5px; overflow-x: auto; }
            .success { color: green; }
            .error { color: red; }
            .test-section { margin-bottom: 30px; border: 1px solid #ddd; padding: 15px; border-radius: 5px; }
            button { padding: 8px 16px; margin: 5px; cursor: pointer; }
        </style>
    </head>
    <body>
        <h1>Docker Ollama Network Test</h1>

        <div class="test-section">
            <h2>Network Diagnostics</h2>
            <button id="network-test-btn">Run Network Test</button>
            <pre id="network-test-results">Click "Run Network Test" to check connectivity</pre>
        </div>

        <div class="test-section">
            <h2>Ollama Configuration</h2>
            <p>Current configuration:</p>
            <pre id="current-config">Loading...</pre>

            <div>
                <label for="base_url">Ollama Base URL:</label>
                <input type="text" id="base_url" style="width: 300px;" placeholder="http://ollama:11434">
                <button id="update-ollama-btn">Update</button>
            </div>
            <p><small>Docker containers should use <code>http://ollama:11434</code>, local dev might use <code>http://localhost:11434</code></small></p>
        </div>

        <div class="test-section">
            <h2>Test Model Query</h2>
            <button id="test-query-btn">Test Query</button>
            <pre id="query-results">Click "Test Query" to run a simple query</pre>
        </div>

        <script>
            // Load current config
            function loadConfig() {
                $.ajax({
                    url: '/api/ollama-config',
                    method: 'GET',
                    success: function(data) {
                        $('#current-config').text(JSON.stringify(data, null, 2));
                        $('#base_url').val(data.base_url || '');
                    },
                    error: function(xhr, status, error) {
                        $('#current-config').html('<span class="error">Error loading config: ' + error + '</span>');
                    }
                });
            }

            // Update Ollama URL
            $('#update-ollama-btn').click(function() {
                const newUrl = $('#base_url').val().trim();
                if (!newUrl) {
                    alert('Please enter a base URL');
                    return;
                }

                $.ajax({
                    url: '/api/ollama-config',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({ base_url: newUrl }),
                    success: function(data) {
                        $('#current-config').text(JSON.stringify(data, null, 2));
                        alert('Configuration updated successfully');
                    },
                    error: function(xhr, status, error) {
                        alert('Error updating configuration: ' + error);
                    }
                });
            });

            // Run network test
            $('#network-test-btn').click(function() {
                $('#network-test-results').text('Running tests...');

                $.ajax({
                    url: '/api/network-test',
                    method: 'GET',
                    success: function(data) {
                        $('#network-test-results').text(JSON.stringify(data, null, 2));
                    },
                    error: function(xhr, status, error) {
                        $('#network-test-results').html('<span class="error">Error running tests: ' + error + '</span>');
                    }
                });
            });

            // Test query
            $('#test-query-btn').click(function() {
                $('#query-results').text('Running query test...');

                $.ajax({
                    url: '/api/improve-text',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({
                        text: "I am good at working with people",
                        type: "tenet"
                    }),
                    success: function(data) {
                        $('#query-results').text(JSON.stringify(data, null, 2));
                    },
                    error: function(xhr, status, error) {
                        $('#query-results').html('<span class="error">Error: ' + error + '</span><br><pre>' + xhr.responseText + '</pre>');
                    }
                });
            });

            // Initialize
            $(document).ready(function() {
                loadConfig();
            });
        </script>
    </body>
    </html>
    '''


# You'll also need to add 'import time' at the top of your file for the network-test endpoint

@app.route("/summary", methods=["GET", "POST"])
def summary():
    if request.method == 'POST':
        worker.update_summary(request.form)
        query.purge_cache("summary")
    return render_template("summary_index.html", **fatten(query.get_summary()))

@app.route("/education", methods=["GET", "POST"])
def education():
    if request.method == 'POST':
        worker.update_education(request.form)
        query.purge_cache("education")
    return render_template("education_index.html", ddpayload=worker.dropdowns("education"), **fatten(query.get_education()))


# @app.route("/certifications", methods=["GET", "POST"])
# def certifications():
#     if request.method == 'POST':
#         worker.certifications(request.form)
#         query.purge_cache("certifications")
#     return render_template("certifications_index.html", **fatten(query.get_certifications()))
@app.route("/certifications", methods=["GET", "POST"])
def certifications():
    if request.method == 'POST':
        worker.certifications(request.form)
        query.purge_cache("certifications")

    # Custom handling for certifications
    # Get raw data
    raw_certs = query.get_certifications()

    # Group certifications by ID
    cert_groups = {}
    for cert in raw_certs:
        cert_id = cert["id"]
        if cert_id not in cert_groups:
            cert_groups[cert_id] = {"id": cert_id, "state": cert["state"]}

        # Add the attribute (certification or year)
        cert_groups[cert_id][cert["attr"]] = cert["value"]

    # Convert grouped data to list for template
    processed_certs = list(cert_groups.values())

    # Create payload with correct structure
    payload = {"payload": processed_certs, "attrs": ["certification", "year"]}

    return render_template("certifications_index.html", **payload)


@app.route("/skills", methods=["GET", "POST"])
def skills():
    if request.method == 'POST':
        worker.update_skills(request.form)
        query.purge_cache("skills")

    # Get dropdown data
    dropdown_data = worker.dropdowns("skills")

    # Get raw skills data
    raw_skills = query.get_skills()

    # Group skills by ID
    skills_groups = {}
    for skill in raw_skills:
        skill_id = skill["id"]
        if skill_id not in skills_groups:
            skills_groups[skill_id] = {
                "id": skill_id,
                "state": skill.get("state", False)
            }

        # Add each attribute to the grouped object
        attr_name = skill["attr"]
        skills_groups[skill_id][attr_name] = skill["value"]

    # Convert grouped data to list for template
    processed_skills = list(skills_groups.values())

    # Create payload with correct structure
    payload = {
        "payload": processed_skills,
        "attrs": ["category", "subcategory", "employer", "employername",
                  "position", "positionname", "shortdesc", "longdesc"]
    }

    return render_template("skills_index.html",
                           ddpayload=dropdown_data,
                           **payload)


@app.route("/employment", methods=["GET", "POST"])
def positions():
    if request.method == 'POST':
        worker.update_positions(request.form)
        query.purge_cache("positions")
    return render_template("employment_index.html", ddpayload=worker.dropdowns("employment"), **fatten(query.get_positions()))



@app.route("/employment", methods=["GET", "POST"])
def positions():
    if request.method == 'POST':
        worker.update_positions(request.form)
        query.purge_cache("positions")
    return render_template("employment_index.html", ddpayload=worker.dropdowns("employment"),
                           **fatten(query.get_positions()))

    # Get dropdown data
    dropdown_data = worker.dropdowns("achievements")

    # Get raw achievement data
    raw_achievements = query.get_achievements()

    # Group achievements by ID
    achievement_groups = {}
    for achievement in raw_achievements:
        achievement_id = achievement["id"]
        if achievement_id not in achievement_groups:
            achievement_groups[achievement_id] = {
                "id": achievement_id,
                "state": achievement.get("state", False)
            }

        # Add each attribute to the grouped object
        attr_name = achievement["attr"]
        achievement_groups[achievement_id][attr_name] = achievement["value"]

    # Convert grouped data to list for template
    processed_achievements = list(achievement_groups.values())

    # Create payload with correct structure
    payload = {
        "payload": processed_achievements,
        "attrs": ["employer", "employername", "position", "positionname",
                  "achievement", "shortdesc", "longdesc", "employerstate",
                  "positionstate", "achievementstate"]
    }

    return render_template("achievements_index.html",
                           ddpayload=dropdown_data,
                           **payload)

@app.route("/glossary", methods=["GET", "POST"])
def glossary():
    if request.method == 'POST':
        worker.update_glossary(request.form)
        query.purge_cache("glossary")
    return render_template("glossary_index.html", **fatten(query.get_glossary()))


@app.route("/generate/one-page", methods=["GET"])
def one_page_doc():
    generator = onePage.Generator()
    generator.run()
    return send_from_directory(uploads, 'one-page.pdf')


@app.route("/generate/hybrid", methods=["GET"])
def hybrid_doc():
    generator = hybrid.Generator()
    generator.run()
    return send_from_directory(uploads, 'hybrid.pdf')


@app.route("/api/ollama-config", methods=["GET", "POST", "OPTIONS"])
def ollama_config():
    """Get or update Ollama configuration"""
    # Handle OPTIONS requests (for CORS preflight)
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        return response

    # For GET requests, return the current config
    if request.method == "GET":
        return jsonify({
            "base_url": ai_service.base_url,
            "model": ai_service.model,
            "enabled": ai_service.ai_enabled
        })

    # For POST requests, update the config
    try:
        # Check for JSON data
        if not request.is_json:
            return jsonify({"error": "Expected JSON data"}), 400

        data = request.json
        print(f"Received config update: {data}")

        # Update base_url if provided
        if "base_url" in data and data["base_url"].strip():
            ai_service.base_url = data["base_url"].strip()

        # Update model if provided
        if "model" in data and data["model"].strip():
            ai_service.model = data["model"].strip()

        # Update enabled status if provided
        if "enabled" in data:
            ai_service.ai_enabled = bool(data["enabled"])

        # Return the updated configuration
        return jsonify({
            "base_url": ai_service.base_url,
            "model": ai_service.model,
            "enabled": ai_service.ai_enabled,
            "message": "Configuration updated successfully"
        })
    except Exception as e:
        import traceback
        print(f"Error in ollama_config: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": f"Server error: {str(e)}"}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port, use_reloader=False)