import os
from flask import redirect, session, request, url_for, flash, render_template, Flask, jsonify
import requests
import logging
from pylaform.services.proxycurl_service import ProxycurlService
from pylaform.services.import_service import ImportService
from pylaform.commands.db.query import Queries
from pylaform.commands.templateWorker import Worker
from pylaform.latex_templates import hybrid, onePage
from pylaform.utilities.commands import fatten, listify, date_adapter
from pylaform.services.ai_service import OllamaService
from pylaform.services.config_service import ConfigService
from pylaform.routes.linkedin_routes import linkedin_bp

# Add or update this near the top of app.py, before the Flask app is created
import logging

# Near the top of app.py, add import
import sqlite3
from flask import flash

# After the imports and before creating app instance
# Set up logging
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check if data directory exists and is writable
data_dir = os.path.join(os.path.abspath(os.curdir), "data")
if not os.path.exists(data_dir):
    try:
        os.makedirs(data_dir, exist_ok=True)
        os.chmod(data_dir, 0o777)  # Full permissions for debugging
        logger.info(f"Created data directory with full permissions")
    except Exception as e:
        logger.error(f"Failed to create data directory: {e}")


# Create the Flask application
app = Flask(__name__, template_folder='pylaform/templates', static_folder='pylaform/static')
app.config.from_pyfile('pylaform/config.py', silent=True)
app.secret_key = "pylaformdb"  # Required for flashing messages

# Initialize database connection with fallback to read-only mode
read_only_mode = False
try:
    query = Queries()
except sqlite3.OperationalError as e:
    if "readonly database" in str(e):
        logger.warning("Database is read-only. Trying to initialize in read-only mode.")
        # Monkey patch the connect function to use read-only mode
        from pylaform.commands.db import connect

        original_db = connect.db
        connect.db = lambda disable_cache=True: original_db(disable_cache, read_only=True)

        # Now try again with read-only mode
        try:
            query = Queries()
            read_only_mode = True
            logger.warning("Application running in READ-ONLY mode. Data modifications won't be saved.")
        except Exception as e2:
            logger.error(f"Failed to initialize database even in read-only mode: {e2}")
            query = None
    else:
        logger.error(f"Failed to initialize database: {e}")
        query = None

# Initialize worker based on database connection status
worker = Worker() if query else None

# Display read-only warning if applicable
if read_only_mode:
    @app.before_request
    def before_request():
        flash("Application is running in READ-ONLY mode. Changes won't be saved to the database.", "warning")

@app.route("/")
def landing():
    # Get the identification data
    identification_data = query.get_identification()

    # Return the template with the complete identification data
    return render_template("landing.html", payload=identification_data)

def get_ollama_service():
    ai_config = config_service.get_ai_config()

    # If AI is not enabled, return with default settings
    if not ai_config.get('enabled', False):
        return OllamaService()

    # Get Ollama configuration
    ollama_config = ai_config.get('ollama', {})
    host = ollama_config.get('host', 'localhost')
    port = ollama_config.get('port', '11434')
    model = ollama_config.get('model', 'gemma3:1b')

    # Create service with configuration
    return OllamaService(host=host, port=port, model=model)

@app.route("/api/ai-status", methods=["GET"])
def ai_status():
    """Check if the Ollama service is available"""
    try:
        # Simple health check
        response = requests.get(f"{ai_service.base_url}/api/tags")
        if response.status_code == 200:
            return jsonify({"status": "ok", "models": response.json().get("models", [])})
        else:
            return jsonify({"status": "error", "message": f"Ollama returned status code {response.status_code}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/api/test-ai-connection', methods=['POST'])
def test_ai_connection():
    from pylaform.services.ai_service import OllamaService
    import traceback

    try:
        # Get request data
        data = request.json
        host = data.get('host', 'localhost')
        port = data.get('port', '11434')
        model = data.get('model', 'gemma3:1b')

        # Create Ollama service with provided configuration
        ollama_service = OllamaService(host=host, port=port, model=model)

        # Test connection
        result = ollama_service.test_connection()

        return jsonify(result)
    except Exception as e:
        print(f"Error testing connection: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/download-model', methods=['POST'])
def download_model():
    """API endpoint to download an Ollama model"""
    # Get request data
    data = request.json
    model = data.get('model')

    # Validate input
    if not model:
        return jsonify({"success": False, "error": "No model specified"}), 400

    # Get host and port from current config
    ai_config = config_service.get_ai_config()
    ollama_config = ai_config.get('ollama', {})
    host = ollama_config.get('host', 'localhost')
    port = ollama_config.get('port', '11434')

    # Create Ollama service with configuration
    ollama_service = OllamaService(host=host, port=port, model=model)

    # Initiate model download
    result = ollama_service.download_model(model)

    # Return result
    return jsonify(result)


@app.route('/api/model-status', methods=['GET'])
def get_model_status():
    """API endpoint to get the status of installed Ollama models"""
    # Get host and port from current config
    ai_config = config_service.get_ai_config()
    ollama_config = ai_config.get('ollama', {})
    host = ollama_config.get('host', 'localhost')
    port = ollama_config.get('port', '11434')

    # Create Ollama service with configuration
    ollama_service = OllamaService(host=host, port=port)

    # Get model status
    result = ollama_service.get_model_status()

    return jsonify(result)

@app.route('/api/improve-text', methods=['POST'])
def improve_text():
    # Get AI configuration
    ai_config = config_service.get_ai_config()

    # Check if AI is enabled
    if not ai_config.get('enabled', False):
        return jsonify({"error": "AI features are not enabled. Please enable them in AI Configuration."})

    # Get the Ollama service with current configuration
    ollama_service = get_ollama_service()

    # Process the improvement request
    data = request.json
    text = data.get('text', '')
    improvement_type = data.get('type', '')

    # Validate input
    if not text or not improvement_type:
        return jsonify({"error": "Missing text or improvement type"})

    # Generate improvement
    result = ollama_service.generate_improvement(text, improvement_type)

    return jsonify(result)


@app.route("/career_customize", methods=["GET", "POST"])
def career_customize():
    if request.method == 'GET':
        return render_template("career_customize.html")

    # Process form submission
    try:
        # Log request for debugging
        app.logger.info("Processing career customize request")

        career_title = request.form.get('career_title', '')
        job_description = request.form.get('job_description', '')
        selected_sections = request.form.getlist('sections[]')
        customization_style = request.form.get('customization_style', 'professional')

        # Validate inputs
        if not career_title or not job_description:
            app.logger.warning("Missing required fields: career_title or job_description")
            flash("Please provide both a career title and job description.", "warning")
            return render_template("career_customize.html")

        if not selected_sections:
            app.logger.warning("No sections selected for customization")
            flash("Please select at least one section to customize.", "warning")
            return render_template("career_customize.html")

        # Get the AI service
        ollama_service = get_ollama_service()

        # Test connection to Ollama service
        connection_test = ollama_service.test_connection()
        if 'error' in connection_test:
            app.logger.error(f"Failed to connect to Ollama service: {connection_test['error']}")
            flash(f"Could not connect to AI service: {connection_test['error']}", "danger")
            return render_template("career_customize.html")

        # Analyze the job description for key requirements
        job_analysis = ollama_service.analyze_job_description(job_description, career_title)

        # Dictionary to store customized content for each section
        customized_data = {}

        app.logger.info(f"Starting customization for sections: {selected_sections}")

        # For each selected section, retrieve active entries and customize
        if 'summary' in selected_sections:
            # Process summary section
            app.logger.info("Processing summary section")
            # Get raw summary data
            raw_summaries = query.get_summary()

            # Group summaries by ID
            summary_groups = {}
            for summary in raw_summaries:
                summary_id = summary["id"]
                if summary_id not in summary_groups:
                    summary_groups[summary_id] = {
                        "id": summary_id,
                        "state": summary.get("state", False)
                    }

                # Add each attribute
                attr_name = summary["attr"]
                if attr_name in ["shortdesc", "longdesc"]:
                    summary_groups[summary_id][attr_name] = summary["value"]

            # Convert to list
            active_summaries = [s for s in summary_groups.values() if s.get("state", False)]

            app.logger.info(f"Found {len(active_summaries)} active summaries")

            # Customize summaries if there are active ones
            if active_summaries:
                customized_summaries = ollama_service.customize_resume_content(
                    section_type='summary',
                    entries=active_summaries,
                    career_title=career_title,
                    job_description=job_description,
                    style=customization_style
                )
                customized_data['summary'] = customized_summaries
                app.logger.info(f"Successfully customized {len(customized_summaries)} summaries")
            else:
                app.logger.warning("No active summaries found to customize")

        # Similar processing for other sections would go here
        # ...

        app.logger.info("Customization complete, rendering preview")
        # Return preview template with job analysis and customized content
        return render_template(
            'career_customize_preview.html',
            career_title=career_title,
            job_analysis=job_analysis,
            customized_sections=customized_data
        )

    except Exception as e:
        app.logger.error(f"Error in career_customize: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        flash(f"An error occurred during customization: {str(e)}", "danger")
        return render_template("career_customize.html")


@app.route("/apply_customization", methods=["POST"])
def apply_customization():
    """Apply the selected customized content to the resume"""
    from datetime import datetime
    import re  # Add this import for string cleaning

    # Track how many changes were made
    changes_made = 0

    # Get career title for labeling
    career_title = request.form.get('career_title', 'Targeted Role')
    timestamp = datetime.now().strftime("%Y-%m-%d")

    # Clean the career title to remove problematic characters for SQL
    clean_career_title = re.sub(r'[,\'"]', '-', career_title)
    customized_label = f"[{clean_career_title} - {timestamp}]"

    # Process summary section changes
    for key in request.form:
        if key.endswith('_action') and request.form[key] == 'accept':
            # Extract section and ID from the key
            parts = key.split('_')
            section = parts[0]
            entry_id = parts[1]

            if section == 'summary':
                try:
                    # Get the original and customized content
                    original_id = request.form.get(f'summary_{entry_id}_original_id')
                    customized_shortdesc = request.form.get(f'summary_{entry_id}_customized_shortdesc')
                    customized_longdesc = request.form.get(f'summary_{entry_id}_customized_longdesc')

                    if not original_id or not customized_shortdesc or not customized_longdesc:
                        app.logger.error(f"Missing required data for summary_{entry_id}")
                        continue

                    # Clean the content for SQL safety
                    customized_shortdesc = customized_shortdesc.replace("'", "''")
                    customized_longdesc = customized_longdesc.replace("'", "''")

                    app.logger.info(f"Processing summary entry: original_id={original_id}")

                    # STEP 1: Disable the original entry
                    try:
                        # Direct SQL update to set state=0
                        app.logger.info(f"Disabling original entry: {original_id}")
                        worker.cursor.execute("UPDATE summary SET state = 0 WHERE id = ?", (original_id,))
                        worker.conn.commit()
                    except Exception as e:
                        app.logger.error(f"Error disabling original entry: {e}")
                        # Try an alternative method if the first fails
                        try:
                            worker.update.single_item("summary", {
                                "id": original_id,
                                "attr": "state",
                                "value": 0,
                                "state": False
                            })
                        except Exception as e2:
                            app.logger.error(f"Second attempt failed: {e2}")

                    # STEP 2: Create a new entry with customized content and explicit state=1
                    try:
                        app.logger.info("Creating new customized entry")
                        # Explicitly include state=1 in the insert
                        worker.cursor.execute(
                            """
                            INSERT INTO summary
                                (shortdesc, longdesc, summaryorder, state)
                            VALUES (?, ?, ?, 1)
                            """,
                            (
                                f"{customized_shortdesc} {customized_label}",
                                customized_longdesc,
                                99  # Default to end of list
                            )
                        )
                        worker.conn.commit()
                        changes_made += 1
                        app.logger.info(f"Successfully created new entry for {original_id}")
                    except Exception as e:
                        app.logger.error(f"Error creating new entry: {e}")
                        # Try an alternative method if the first fails
                        try:
                            worker.insert.multi_column("summary",
                                                       shortdesc=f"{customized_shortdesc} {customized_label}",
                                                       longdesc=customized_longdesc,
                                                       summaryorder=99,
                                                       state=1
                                                       )
                            changes_made += 1
                        except Exception as e2:
                            app.logger.error(f"Second insert attempt failed: {e2}")

                except Exception as e:
                    app.logger.error(f"Error processing summary entry {entry_id}: {e}")

    # Make sure all changes are committed
    worker.conn.commit()

    # Clear cache to ensure changes are immediately visible
    try:
        worker.query.purge_cache("summary")
    except:
        pass

    # Redirect to appropriate page based on changes
    if changes_made > 0:
        flash(f"{changes_made} resume entries were successfully customized for {career_title}!", "success")
    else:
        flash("No changes were applied to your resume.", "info")

    return redirect(url_for('landing'))

@app.route("/information", methods=["GET", "POST"])
def information():
    if request.method == 'POST':
        worker.identification(request.form)
        query.purge_cache("identification")
    return render_template("information.html", **fatten(query.get_identification()))


# Modified version of the summary route in app.py
@app.route("/summary", methods=["GET", "POST"])
def summary():
    """Summary route."""
    if request.method == "POST":
        worker.update_summary(request.form)

        # Run cleanup after processing the form
        worker.delete.cleanup_disabled_entries(["summary"])

        # Clear cache to ensure changes are immediately visible
        worker.query.purge_cache("summary")

        return redirect(url_for("summary"))

    # Get summary data
    summary_data = worker.query.get_summary()

    # Add debugging
    print(f"Raw summary data count: {len(summary_data)}")
    unique_ids = set(item["id"] for item in summary_data)
    print(f"Unique summary IDs: {unique_ids}")

    # Group the summary items by ID to create the payload expected by the template
    summary_by_id = {}
    for item in summary_data:
        item_id = item["id"]

        # Initialize the dictionary for this ID if not already present
        if item_id not in summary_by_id:
            summary_by_id[item_id] = {
                "id": item_id,
                "state": item["state"]
            }

        # Add each attribute to the grouped item
        attr_name = item["attr"]
        summary_by_id[item_id][attr_name] = item["value"]

    # Debug the grouped data
    print(f"Grouped summary items count: {len(summary_by_id)}")
    for item_id, item_data in summary_by_id.items():
        print(f"  ID {item_id}: {item_data.get('shortdesc', 'NO_SHORTDESC')} (state: {item_data.get('state')})")

    # Convert the grouped data to a list
    payload = list(summary_by_id.values())

    # Debug the final payload
    print(f"Final payload count: {len(payload)}")

    # Sort by summaryorder if available (default to 0)
    payload.sort(key=lambda x: x.get("summaryorder", 0))

    # Render the template with the payload
    return render_template("summary_index.html", payload=payload)

@app.route('/ai-config', methods=['GET', 'POST'])
@app.route('/ai-config', methods=['GET', 'POST'])
def ai_config():
    # Use the global config_service instead of creating a new one
    # from pylaform.services.config_service import ConfigService
    # config_service = ConfigService()

    if request.method == 'POST':
        # Get form data
        ai_enabled = 'aiEnabledToggle' in request.form
        host = request.form.get('ollamaServerHost', 'localhost')
        port = request.form.get('ollamaServerPort', '11434')

        # Handle model selection
        model_select = request.form.get('ollamaModel')
        if model_select == 'custom':
            model = request.form.get('customOllamaModel', 'gemma3:1b')
        else:
            model = model_select

        # Save configuration
        config_service.save_ai_config(ai_enabled, host, port, model)

        # Redirect to the same page to prevent form resubmission
        return redirect(url_for('ai_config'))

    # Get current configuration
    ai_config = config_service.get_ai_config()

    # Render the template with current configuration
    return render_template('ai_config.html',
                           ai_enabled=ai_config.get('enabled', False),
                           ollama_server_host=ai_config.get('ollama', {}).get('host', 'localhost'),
                           ollama_server_port=ai_config.get('ollama', {}).get('port', '11434'),
                           ollama_model=ai_config.get('ollama', {}).get('model', 'gemma3:1b'))

@app.route("/education", methods=["GET", "POST"])
def education():
    if request.method == 'POST':
        # Instead of modifying the request.form object (which is immutable),
        # we'll pass it directly to the worker and let it handle date processing
        worker.update_education(request.form)
        query.purge_cache("education")
        return redirect(url_for('education'))

    # For GET requests, render the template with data
    return render_template(
        "education_index.html",
        ddpayload=worker.dropdowns("education"),
        **fatten(query.get_education())
    )


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


@app.route("/achievements", methods=["GET", "POST"])
def achievements():
    if request.method == 'POST':
        worker.update_achievements(request.form)
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
        "attrs": ["employer", "employername", "school", "schoolname", "position", "positionname",
                  "achievement", "shortdesc", "longdesc", "employerstate",
                  "positionstate", "schoolstate", "achievementstate"]
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
    # Import os at the function level to ensure it's available throughout the function
    import os
    import glob
    import traceback  # Add this for better error tracking

    # Get force parameter from URL
    force = request.args.get('force', 'false').lower() == 'true'

    # Delete existing files if force=true
    if force:
        # Remove all one-page.* files
        for file_path in glob.glob(os.path.join(app.root_path, 'data', 'one-page.*')):
            try:
                os.remove(file_path)
                print(f"Removed {file_path}")
            except Exception as e:
                print(f"Failed to remove {file_path}: {e}")

    try:
        # Create and run the generator
        from pylaform.latex_templates.onePage import Generator
        generator = Generator()

        # Print the generator's methods to check for process_achievements
        print("Method signatures:")
        import inspect
        for name, method in inspect.getmembers(generator, predicate=inspect.ismethod):
            if name.startswith('process_'):
                sig = inspect.signature(method)
                print(f"{name}{sig}")

        # Run the generator
        generator.run()

        # Check if the PDF was actually created, regardless of whether errors occurred
        pdf_path = os.path.join(uploads, 'one-page.pdf')

        # Additional validation to ensure the PDF exists and is valid
        if os.path.exists(pdf_path):
            # Check the file size to ensure it's not empty
            if os.path.getsize(pdf_path) > 0:
                print(f"PDF found at {pdf_path} with size {os.path.getsize(pdf_path)} bytes")
                return send_from_directory(uploads, 'one-page.pdf')
            else:
                return jsonify({"error": "PDF file exists but is empty"}), 500
        else:
            return jsonify({"error": "PDF file was not created"}), 500

    except ImportError as e:
        return jsonify({"error": f"Import error: {str(e)}"}), 500
    except Exception as e:
        print(f"Exception in one_page_doc route: {str(e)}")
        traceback.print_exc()  # Print the full traceback for better debugging

        # As a fallback, check if PDF exists anyway (it might have been created despite errors)
        pdf_path = os.path.join(uploads, 'one-page.pdf')
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
            print(f"Despite errors, PDF exists and will be served")
            return send_from_directory(uploads, 'one-page.pdf')
        else:
            return jsonify({"error": f"Failed to generate PDF: {str(e)}"}), 500

@app.route("/generate/hybrid", methods=["GET"])
def hybrid_doc():
    generator = hybrid.Generator()
    generator.run()
    return send_from_directory(uploads, 'hybrid.pdf')


@app.route("/api/delete", methods=["POST"])
def api_delete():
    """API endpoint to handle deletion of entries"""
    table = request.form.get("table")
    entry_id = request.form.get("id")
    hard_delete = request.form.get("hard_delete", "false").lower() == "true"

    if not table or not entry_id:
        return jsonify({"success": False, "error": "Missing table or ID"}), 400

    try:
        # Convert ID to integer
        entry_id = int(entry_id)
    except ValueError:
        return jsonify({"success": False, "error": f"Invalid ID: {entry_id}"}), 400

    # Check if the table is valid
    valid_tables = ["summary", "school", "focus", "employer", "position",
                    "achievement", "skill", "certification", "glossary"]
    if table not in valid_tables:
        return jsonify({"success": False, "error": f"Invalid table: {table}"}), 400

    result = worker.delete.delete_entry(table, entry_id, hard_delete)

    if result:
        # Clear cache for this table
        try:
            worker.query.purge_cache(table)
        except:
            app.logger.warning(f"Failed to purge cache for {table}")

        return jsonify({"success": True, "message": f"Deleted entry {entry_id} from {table}"}), 200
    else:
        return jsonify({"success": False, "error": "Failed to delete entry"}), 500


@app.route('/auth/linkedin/callback')
def linkedin_callback():
    """Handle LinkedIn OAuth callback"""
    # Get code and state from request
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')

    # Validate the state to prevent CSRF
    if error or not code or state != session.get('linkedin_state'):
        flash("Authentication failed or was cancelled", "danger")
        return redirect(url_for('linkedin_import_page'))

    # Clean up the state from session
    session.pop('linkedin_state', None)

    try:
        # Exchange code for access token
        linkedin = LinkedInService()
        token_data = linkedin.exchange_code_for_token(code)

        # Store token in session
        session['linkedin_token'] = token_data

        # Redirect to the import page
        return redirect(url_for('linkedin_import_page'))
    except Exception as e:
        flash(f"Failed to complete authentication: {str(e)}", "danger")
        return redirect(url_for('linkedin_import_page'))


@app.route('/linkedin/import', methods=['POST'])
def linkedin_import():
    """Process the LinkedIn data import"""
    # Check if we have an active token and profile data
    token = session.get('linkedin_token')
    profile_data = session.get('linkedin_profile_data')

    if not token or not profile_data:
        flash("LinkedIn data not available. Please reconnect your account.", "danger")
        return redirect(url_for('linkedin_import_page'))

    # Get selected sections to import
    import_sections = request.form.getlist('import_sections')

    if not import_sections:
        flash("Please select at least one section to import", "warning")
        return redirect(url_for('linkedin_import_page'))

    try:
        # Import basic information
        if 'basic_info' in import_sections:
            from pylaform.commands.db import update, query
            updater = update.Updates()

            # Create identification data packet
            identification = []
            if profile_data.get('firstName') and profile_data.get('lastName'):
                identification.append({
                    'attr': 'name',
                    'value': f"{profile_data['firstName']} {profile_data['lastName']}",
                    'state': 1
                })

            if profile_data.get('email'):
                identification.append({
                    'attr': 'email',
                    'value': profile_data['email'],
                    'state': 1
                })

            # Update identification data
            for item in identification:
                if item['value']:  # Only update if we have a value
                    try:
                        updater.inverted_single_item('identification', item)
                    except Exception as e:
                        app.logger.error(f"Error updating identification item {item['attr']}: {str(e)}")

        # Import work experience
        if 'experience' in import_sections and 'positions' in profile_data and profile_data['positions']:
            from pylaform.commands.db import query, update, delete
            updater = update.Updates()
            deleter = delete.Deletes()

            try:
                # Get existing employment records
                employment_data = query.Queries().get_positions()

                # Delete existing records
                for item in employment_data:
                    deleter.single_row('positions', item['id'])
            except Exception as e:
                app.logger.error(f"Error clearing existing employment data: {str(e)}")

            # Now add LinkedIn positions
            for idx, position in enumerate(profile_data['positions']):
                try:
                    # Create position data
                    position_data = {
                        'id': idx + 1,  # Use index-based ID
                        'company': position.get('company', {}).get('name', ''),
                        'title': position.get('title', ''),
                        'description': position.get('summary', ''),
                        'startmonth': position.get('startDate', {}).get('month', ''),
                        'startyear': position.get('startDate', {}).get('year', ''),
                        'state': 1,
                    }

                    # Handle end date or current position
                    if position.get('current', False):
                        position_data['present'] = 1
                    else:
                        position_data['endmonth'] = position.get('endDate', {}).get('month', '')
                        position_data['endyear'] = position.get('endDate', {}).get('year', '')

                    # Insert new position
                    updater.multi_column('positions', **position_data)
                except Exception as e:
                    app.logger.error(f"Error adding position {idx}: {str(e)}")

        # Import education
        if 'education' in import_sections and 'education' in profile_data and profile_data['education']:
            from pylaform.commands.db import query, update, delete
            updater = update.Updates()
            deleter = delete.Deletes()

            try:
                # Get existing education records
                education_data = query.Queries().get_education()

                # Delete existing records
                for item in education_data:
                    deleter.single_row('education', item['id'])
            except Exception as e:
                app.logger.error(f"Error clearing existing education data: {str(e)}")

            # Now add LinkedIn education
            for idx, school in enumerate(profile_data['education']):
                try:
                    # Create education data
                    education_data = {
                        'id': idx + 1,  # Use index-based ID
                        'school': school.get('schoolName', ''),
                        'degree': school.get('degree', ''),
                        'field': school.get('fieldOfStudy', ''),
                        'startyear': school.get('startDate', {}).get('year', ''),
                        'state': 1,
                    }

                    # Handle end date
                    if 'endDate' in school and school['endDate']:
                        education_data['endyear'] = school['endDate'].get('year', '')
                    else:
                        education_data['present'] = 1

                    # Insert new education
                    updater.multi_column('education', **education_data)
                except Exception as e:
                    app.logger.error(f"Error adding education {idx}: {str(e)}")

        # Import skills
        if 'skills' in import_sections and 'skills' in profile_data and profile_data['skills']:
            from pylaform.commands.db import query, update, delete
            updater = update.Updates()
            deleter = delete.Deletes()

            try:
                # Get existing skills records
                skills_data = query.Queries().get_skills()

                # Delete existing records
                for item in skills_data:
                    deleter.single_row('skills', item['id'])
            except Exception as e:
                app.logger.error(f"Error clearing existing skills data: {str(e)}")

            # Now add LinkedIn skills
            for idx, skill in enumerate(profile_data['skills']):
                try:
                    # Create skill data
                    skill_data = {
                        'id': idx + 1,  # Use index-based ID
                        'shortdesc': skill.get('name', ''),
                        'longdesc': '',  # LinkedIn doesn't provide detailed skill descriptions
                        'rating': 4,  # Default to high rating
                        'state': 1,
                    }

                    # Insert new skill
                    updater.multi_column('skills', **skill_data)
                except Exception as e:
                    app.logger.error(f"Error adding skill {idx}: {str(e)}")

        flash("LinkedIn data successfully imported!", "success")

        # Clear the session data to avoid duplicate imports
        session.pop('linkedin_profile_data', None)

        # Redirect to the main resume page
        return redirect(url_for('landing'))

    except Exception as e:
        app.logger.error(f"Error importing LinkedIn data: {str(e)}")
        flash(f"Error importing LinkedIn data: {str(e)}", "danger")
        return redirect(url_for('linkedin_import_page'))


@app.route('/linkedin/error')
def linkedin_error():
    """Display LinkedIn connection error page"""
    error_title = request.args.get('title', 'Connection Error')
    error_message = request.args.get('message', 'An error occurred while connecting to LinkedIn.')

    return render_template(
        'linkedin_error.html',
        error_title=error_title,
        error_message=error_message
    )

@app.route('/linkedin-import')
def linkedin_import_page():
    """LinkedIn import page"""
    # Check if Proxycurl API key is configured
    has_proxycurl = bool(os.environ.get('PROXYCURL_API_KEY', ''))
    return render_template('linkedin_import.html', has_proxycurl=has_proxycurl)


@app.route('/linkedin-import-with-proxycurl', methods=['POST'])
def linkedin_import_with_proxycurl():
    """Import LinkedIn data using Proxycurl API"""
    logger.info("--- Starting LinkedIn import with Proxycurl ---")

    # Get LinkedIn profile URL from form
    linkedin_url = request.form.get('linkedin_profile_url', '')
    logger.debug(f"LinkedIn URL submitted: {linkedin_url}")

    if not linkedin_url:
        logger.warning("No LinkedIn URL provided")
        flash("Please provide your LinkedIn profile URL", "warning")
        return redirect(url_for('linkedin_import_page'))

    # Validate URL format
    if not (linkedin_url.startswith('https://www.linkedin.com/') or
            linkedin_url.startswith('https://linkedin.com/')):
        logger.warning(f"Invalid LinkedIn URL format: {linkedin_url}")
        flash("Please enter a valid LinkedIn profile URL", "warning")
        return redirect(url_for('linkedin_import_page'))

    # Initialize Proxycurl service
    proxycurl_service = ProxycurlService()
    logger.debug(f"Proxycurl API key configured: {bool(proxycurl_service.api_key)}")

    # Check if API key is configured
    if not proxycurl_service.api_key:
        logger.warning("Proxycurl API key not configured")
        flash("Proxycurl API key not configured. Please configure it in LinkedIn settings.", "warning")
        return redirect(url_for('linkedin_config'))

    # Fetch profile data
    logger.info(f"Fetching LinkedIn profile data from {linkedin_url}")
    profile_data = proxycurl_service.get_profile_data(linkedin_url)

    if 'error' in profile_data:
        logger.error(f"Error from Proxycurl API: {profile_data['error']}")
        flash(f"Error fetching LinkedIn data: {profile_data['error']}", "danger")
        return redirect(url_for('linkedin_import_page'))

    # Log successful data retrieval
    logger.info("Successfully retrieved LinkedIn profile data")
    logger.debug(f"Profile data contains keys: {list(profile_data.keys())}")

    # Get selected sections to import
    import_sections = request.form.getlist('import_sections')
    logger.debug(f"Selected sections to import: {import_sections}")

    # If no sections selected, select all by default
    if not import_sections:
        import_sections = ['basic_info', 'experience', 'education', 'skills']
        logger.debug(f"No sections selected, using defaults: {import_sections}")

    # Process the import
    try:
        logger.info("Starting import processing")
        import_service = ImportService()
        result = import_service.process_linkedin_import(profile_data, import_sections)

        if result['success']:
            sections_imported = ', '.join(result['imported_sections'])
            logger.info(f"LinkedIn import successful. Sections imported: {sections_imported}")
            flash(f"Successfully imported LinkedIn data: {sections_imported}", "success")
        else:
            errors = ', '.join(result['errors'])
            logger.warning(f"LinkedIn import completed with errors: {errors}")
            flash(f"Errors during import: {errors}", "warning")

        # Clear the session data
        if 'linkedin_profile_data' in session:
            logger.debug("Clearing LinkedIn profile data from session")
            session.pop('linkedin_profile_data', None)

        logger.info("LinkedIn import process completed, redirecting to landing page")
        return redirect(url_for('landing'))

    except Exception as e:
        logger.exception(f"Unexpected error during LinkedIn import process: {str(e)}")
        flash(f"Error importing LinkedIn data: {str(e)}", "danger")
        return redirect(url_for('linkedin_import_page'))


@app.route('/linkedin-settings', methods=['GET', 'POST'], endpoint='linkedin.settings')
def linkedin_settings_redirect():

    """LinkedIn settings page - configures Proxycurl API key"""
    # Get current Proxycurl API key from config or environment
    proxycurl_api_key = os.environ.get('PROXYCURL_API_KEY', '')

    # Also try to get from config if using a config file
    try:
        if not proxycurl_api_key and query:
            # Assuming you have a config table or method to retrieve settings
            # Adjust this based on your actual configuration storage method
            pass
    except Exception as e:
        logger.error(f"Error loading Proxycurl API key: {str(e)}")

    # If it's a POST request, save the settings
    if request.method == 'POST':
        proxycurl_api_key = request.form.get('proxycurl_api_key', '')

        # Save API key to environment variable
        os.environ['PROXYCURL_API_KEY'] = proxycurl_api_key

        # Also save to persistent storage if available
        try:
            if query:
                # Example of how you might save to database
                # Adjust this to match your actual storage method
                # query.save_config('proxycurl_api_key', proxycurl_api_key)
                pass

            flash('LinkedIn API settings saved successfully', 'success')
        except Exception as e:
            flash(f'Error saving settings: {str(e)}', 'error')

    # Render the template with current settings
    return render_template(
        'linkedin_settings.html',
        proxycurl_api_key=proxycurl_api_key
    )


@app.route('/linkedin/config')
def linkedin_config():
    """Display LinkedIn configuration page"""
    from pylaform.services.config_service import ConfigService
    config_service = ConfigService()
    config = config_service.get_config()
    linkedin_config = config.get('linkedin', {})

    proxycurl_api_key = linkedin_config.get('proxycurl_api_key', '')

    return render_template(
        'linkedin_config.html',
        proxycurl_api_key=proxycurl_api_key
    )

# if __name__ == '__main__':
#     app.run(debug=True, use_reloader=False, host='0.0.0.0')

if __name__ == '__main__':
    # Check if Ollama environment variables are set
    ollama_host = os.environ.get('OLLAMA_HOST', 'localhost')
    ollama_port = os.environ.get('OLLAMA_PORT', '11434')

    # Log application startup
    logger.info(f"Starting application with Ollama at {ollama_host}:{ollama_port}")

    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)