# Add this import at the top of app.py
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

    result = ai_service.generate_improvement(text, improvement_type)

    if "error" in result:
        return jsonify(result), 500

    return jsonify(result)


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
    generator = onePage.Generator()
    generator.run()
    return send_from_directory(uploads, 'one-page.pdf')


@app.route("/generate/hybrid", methods=["GET"])
def hybrid_doc():
    generator = hybrid.Generator()
    generator.run()
    return send_from_directory(uploads, 'hybrid.pdf')


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
