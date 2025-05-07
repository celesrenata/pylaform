from flask import Flask, render_template, request, send_from_directory, jsonify, redirect, url_for, flash, session
import os
import requests
import json
from pylaform.commands.db.query import Queries
from pylaform.commands.templateWorker import Worker
from pylaform.latex_templates import hybrid, onePage
from pylaform.utilities.commands import fatten, listify, date_adapter
from pylaform.services.ai_service import OllamaService
from pylaform.services.config_service import ConfigService

# Initialize the AI service
ai_service = OllamaService()

# Initialize the config service
config_service = ConfigService()


app = Flask(__name__,
            static_url_path="",
            static_folder="pylaform/static",
            template_folder="pylaform/templates")

# Set a secret key for the application (required for sessions)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'pylaform-dev-secret-key')

# Not currently used.
app.jinja_env.add_extension('jinja2.ext.do')

query = Queries()
worker = Worker()
uploads: str = os.path.join(app.root_path, 'data')

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

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)