from flask_cors import CORS
from flask import Flask, render_template, request, send_from_directory, jsonify
import os
import requests
import json
import traceback
from pylaform.commands.db.query import Queries
from pylaform.commands.templateWorker import Worker
from pylaform.latex_templates import hybrid, onePage
from pylaform.utilities.commands import fatten, listify
from pylaform.services.ai_service import OllamaService

# Initialize the Flask app
app = Flask(__name__,
            static_url_path="",
            static_folder="pylaform/static",
            template_folder="pylaform/templates")

# Enable CORS with more explicit settings
CORS(app, origins="*", supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     methods=["GET", "POST", "OPTIONS"])

app.jinja_env.add_extension('jinja2.ext.do')

# Initialize services
query = Queries()
worker = Worker()
uploads: str = os.path.join(app.root_path, 'data')

# Initialize AI service - with better defaults for Docker compatibility
# The service is initialized here but will be configured later if needed
ai_service = OllamaService(base_url=os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434"))


@app.route("/")
def landing():
    return render_template("landing.html", **fatten(query.get_identification()))


@app.route("/information", methods=["GET", "POST"])
def information():
    if request.method == 'POST':
        worker.identification(request.form)
        query.purge_cache("identification")
    return render_template("information.html", **fatten(query.get_identification()))


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
    return render_template("education_index.html", ddpayload=worker.dropdowns("education"),
                           **fatten(query.get_education()))


@app.route("/certifications", methods=["GET", "POST"])
def certifications():
    if request.method == 'POST':
        worker.certifications(request.form)
        query.purge_cache("certifications")

    # Custom handling for certifications
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
    return render_template("employment_index.html", ddpayload=worker.dropdowns("employment"),
                           **fatten(query.get_positions()))

@app.route("/achievements", methods=["GET", "POST"])
def achievements():
    if request.method == 'POST':
        # Create a mutable copy of the form data
        form_data = request.form.to_dict(flat=True)
        worker.update_achievements(form_data)
        query.purge_cache("achievements")

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


# =====================================================================
# AI SERVICE ENDPOINTS - IMPROVED IMPLEMENTATION
# =====================================================================

@app.route("/api/ai-status", methods=["GET"])
def ai_status():
    """Check if the Ollama service is available and return its status"""
    if not ai_service.ai_enabled:
        return jsonify({
            "status": "disabled",
            "message": "AI service is disabled",
            "base_url": ai_service.base_url,
            "model": ai_service.model
        })

    try:
        # Simple health check
        response = requests.get(f"{ai_service.base_url}/api/tags", timeout=5)

        if response.status_code == 200:
            # Successfully connected to Ollama
            models = []
            try:
                data = response.json()
                models = [model.get("name") for model in data.get("models", [])]
            except Exception as e:
                print(f"Error parsing model data: {str(e)}")

            return jsonify({
                "status": "ok",
                "models": models,
                "base_url": ai_service.base_url,
                "current_model": ai_service.model
            })
        else:
            # Connected but got an error
            return jsonify({
                "status": "error",
                "message": f"Ollama returned status code {response.status_code}",
                "base_url": ai_service.base_url
            })

    except requests.exceptions.Timeout:
        return jsonify({
            "status": "error",
            "message": "Connection timeout when contacting Ollama server",
            "base_url": ai_service.base_url
        })
    except requests.exceptions.ConnectionError:
        return jsonify({
            "status": "error",
            "message": f"Could not connect to Ollama server at {ai_service.base_url}",
            "details": "Make sure Ollama is running and accessible"
        })
    except Exception as e:
        print(f"Error in ai_status: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            "status": "error",
            "message": str(e),
            "base_url": ai_service.base_url
        })


@app.route("/api/improve-text", methods=["POST"])
def improve_text():
    """API endpoint to get AI improvements for resume text"""
    if not request.is_json:
        return jsonify({"error": "Expected JSON data"}), 400

    data = request.json
    text = data.get("text", "").strip()
    improvement_type = data.get("type", "").strip()

    # Validate input
    if not text:
        return jsonify({"error": "Text cannot be empty"}), 400

    if not improvement_type:
        return jsonify({"error": "Improvement type must be specified"}), 400

    # Check if AI is enabled
    if not ai_service.ai_enabled:
        return jsonify({
            "error": "AI service is disabled",
            "ai_disabled": True
        }), 503

    # Call the AI service
    try:
        result = ai_service.generate_improvement(text, improvement_type)

        # If there's an error in the result
        if "error" in result:
            print(f"Error from AI service: {result['error']}")
            return jsonify(result), 500

        return jsonify(result)
    except Exception as e:
        print(f"Exception in improve_text: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


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
    if request.method == "POST":
        try:
            # Check if the request is JSON
            if not request.is_json:
                raw_data = request.get_data(as_text=True)
                if not raw_data:
                    return jsonify({"error": "No data received"}), 400

                # Try to parse as JSON if not already parsed
                try:
                    data = json.loads(raw_data)
                except json.JSONDecodeError as e:
                    return jsonify({
                        "error": f"Invalid JSON data: {str(e)}",
                        "received": raw_data
                    }), 400
            else:
                data = request.json

            # Update configuration if provided
            if "base_url" in data and data["base_url"].strip():
                ai_service.base_url = data["base_url"].strip()

            if "model" in data and data["model"].strip():
                ai_service.model = data["model"].strip()

            if "enabled" in data:
                ai_service.ai_enabled = bool(data["enabled"])

            # Return updated configuration
            return jsonify({
                "base_url": ai_service.base_url,
                "model": ai_service.model,
                "enabled": ai_service.ai_enabled,
                "message": "Configuration updated successfully"
            })
        except Exception as e:
            print(f"Error in ollama_config: {str(e)}")
            print(traceback.format_exc())
            return jsonify({
                "error": f"Server error: {str(e)}"
            }), 500


@app.route("/api/enable-ai", methods=["GET"])
def enable_ai():
    """Simple endpoint to enable AI features"""
    ai_service.ai_enabled = True
    return jsonify({
        "base_url": ai_service.base_url,
        "model": ai_service.model,
        "enabled": ai_service.ai_enabled,
        "message": "AI service enabled successfully"
    })


# =====================================================================
# DIAGNOSTIC ENDPOINTS
# =====================================================================

@app.route("/test-page", methods=["GET"])
def test_page():
    """Test page for API functionality verification"""
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>API Test Page</title>
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <style>
            body { font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }
            pre { background: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; }
            button { padding: 8px 12px; margin: 5px; cursor: pointer; }
            input[type="text"] { padding: 8px; width: 300px; }
            .card { border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin-bottom: 20px; }
            .card h2 { margin-top: 0; }
            .success { color: green; }
            .error { color: red; }
        </style>
    </head>
    <body>
        <h1>Ollama Integration Test</h1>

        <div class="card">
            <h2>Current Config</h2>
            <pre id="current-config">Loading...</pre>
            <button id="refresh-btn">Refresh</button>
            <button id="check-status-btn">Check Ollama Status</button>
        </div>

        <div class="card">
            <h2>Update Config</h2>
            <form id="config-form">
                <div>
                    <label for="base_url">Ollama URL:</label>
                    <input type="text" id="base_url" name="base_url" value="http://ollama:11434">
                </div>
                <div>
                    <label for="model">Model:</label>
                    <input type="text" id="model" name="model" value="llama3.2:1b">
                </div>
                <div>
                    <label for="enabled">Enabled:</label>
                    <input type="checkbox" id="enabled" name="enabled" checked>
                </div>
                <button type="submit">Save</button>
                <button type="button" id="enable-ai-btn">Quick Enable</button>
            </form>
        </div>

        <div class="card">
            <h2>Test Text Improvement</h2>
            <div>
                <label for="improvement-type">Improvement Type:</label>
                <select id="improvement-type">
                    <option value="tenet">Core Principle/Tenet</option>
                    <option value="list">Text to List</option>
                    <option value="sentence_restructure">Restructure Sentence</option>
                    <option value="sentence_summarization">Summarize</option>
                </select>
            </div>
            <div>
                <label for="input-text">Text to Improve:</label>
                <textarea id="input-text" rows="4" style="width: 100%">I try to always make sure my work is done on time and I communicate well with my team members.</textarea>
            </div>
            <button id="improve-btn">Improve Text</button>
            <div>
                <h3>Result:</h3>
                <pre id="result">Results will appear here...</pre>
            </div>
        </div>

        <div class="card">
            <h2>Log</h2>
            <pre id="log"></pre>
            <button id="clear-log">Clear Log</button>
        </div>

        <script>
            // Log function
            function log(message, isError = false) {
                const timestamp = new Date().toISOString();
                const logClass = isError ? 'error' : 'success';
                $('#log').prepend(`<div class="${logClass}">${timestamp}: ${message}</div>`);
            }

            // Load current config
            function loadConfig() {
                log("Fetching current configuration...");
                $.ajax({
                    url: '/api/ollama-config',
                    method: 'GET',
                    success: function(data) {
                        log("Config loaded successfully");
                        $('#current-config').text(JSON.stringify(data, null, 2));

                        // Update form with current values
                        $('#base_url').val(data.base_url || '');
                        $('#model').val(data.model || '');
                        $('#enabled').prop('checked', !!data.enabled);
                    },
                    error: function(xhr, status, error) {
                        log("Error loading config: " + error, true);
                        try {
                            log("Response: " + JSON.stringify(xhr.responseJSON), true);
                        } catch (e) {
                            log("Response text: " + xhr.responseText, true);
                        }
                    }
                });
            }

            // Check Ollama status
            function checkStatus() {
                log("Checking Ollama status...");
                $.ajax({
                    url: '/api/ai-status',
                    method: 'GET',
                    success: function(data) {
                        if (data.status === "ok") {
                            log("Ollama is available! Models: " + JSON.stringify(data.models));
                            $('#current-config').text(JSON.stringify(data, null, 2));
                        } else {
                            log("Ollama status: " + data.status + " - " + data.message, data.status !== "ok");
                            $('#current-config').text(JSON.stringify(data, null, 2));
                        }
                    },
                    error: function(xhr, status, error) {
                        log("Error checking status: " + error, true);
                        try {
                            log("Response: " + JSON.stringify(xhr.responseJSON), true);
                        } catch (e) {
                            log("Response text: " + xhr.responseText, true);
                        }
                    }
                });
            }

            // Test text improvement
            function improveText() {
                const text = $('#input-text').val();
                const type = $('#improvement-type').val();

                if (!text) {
                    log("Error: Text cannot be empty", true);
                    return;
                }

                log("Sending text for improvement...");

                $.ajax({
                    url: '/api/improve-text',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({
                        text: text,
                        type: type
                    }),
                    success: function(data) {
                        log("Text improved successfully!");
                        $('#result').text(data.response || JSON.stringify(data, null, 2));
                    },
                    error: function(xhr, status, error) {
                        log("Error improving text: " + error, true);
                        try {
                            const response = JSON.parse(xhr.responseText);
                            $('#result').text(JSON.stringify(response, null, 2));
                            log("Error details: " + JSON.stringify(response), true);
                        } catch (e) {
                            $('#result').text(xhr.responseText);
                            log("Error response: " + xhr.responseText, true);
                        }
                    }
                });
            }

            // Initialize on page load
            $(document).ready(function() {
                // Initial load
                loadConfig();

                // Set up event handlers
                $('#refresh-btn').click(function(e) {
                    e.preventDefault();
                    loadConfig();
                });

                $('#check-status-btn').click(function(e) {
                    e.preventDefault();
                    checkStatus();
                });

                $('#config-form').submit(function(e) {
                    e.preventDefault();

                    const config = {
                        base_url: $('#base_url').val(),
                        model: $('#model').val(),
                        enabled: $('#enabled').is(':checked')
                    };

                    log("Sending config update: " + JSON.stringify(config));

                    $.ajax({
                        url: '/api/ollama-config',
                        method: 'POST',
                        contentType: 'application/json',
                        data: JSON.stringify(config),
                        success: function(data) {
                            log("Config updated successfully");
                            $('#current-config').text(JSON.stringify(data, null, 2));
                        },
                        error: function(xhr, status, error) {
                            log("Error updating config: " + error, true);
                            try {
                                log("Response: " + JSON.stringify(xhr.responseJSON), true);
                            } catch (e) {
                                log("Response text: " + xhr.responseText, true);
                            }
                        }
                    });
                });

                $('#enable-ai-btn').click(function(e) {
                    e.preventDefault();

                    $.ajax({
                        url: '/api/enable-ai',
                        method: 'GET',
                        success: function(data) {
                            log("AI service enabled successfully");
                            $('#current-config').text(JSON.stringify(data, null, 2));
                            $('#enabled').prop('checked', true);
                        },
                        error: function(xhr, status, error) {
                            log("Error enabling AI: " + error, true);
                        }
                    });
                });

                $('#improve-btn').click(function(e) {
                    e.preventDefault();
                    improveText();
                });

                $('#clear-log').click(function(e) {
                    e.preventDefault();
                    $('#log').empty();
                    log("Log cleared");
                });
            });
        </script>
    </body>
    </html>
    '''


@app.route("/api/test", methods=["GET", "POST"])
def test_endpoint():
    """Test endpoint to verify API functionality"""
    if request.method == "GET":
        return jsonify({"message": "GET request received successfully"})
    else:
        try:
            if request.is_json:
                data = request.json
                return jsonify({
                    "message": "POST request received successfully",
                    "received_data": data
                })
            else:
                return jsonify({
                    "message": "POST request received successfully but no JSON data found",
                    "received_data": request.form.to_dict() if request.form else "No form data"
                })
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route("/api/routes", methods=["GET"])
def list_routes():
    """List all registered routes for debugging"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            "endpoint": rule.endpoint,
            "methods": list(rule.methods),
            "path": str(rule)
        })
    return jsonify({"routes": routes})


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5000)