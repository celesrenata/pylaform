import os

from pylaform.utilities.dbCommands import Queries
from flask import Flask, render_template, request, send_from_directory
from pylaform.utilities.commands import fatten
from pylaform.latex_templates import hybrid, onePage

app = Flask(__name__,
            static_url_path="",
            static_folder="pylaform/static",
            template_folder="pylaform/templates")

resume_data = Queries()
uploads = os.path.join(app.root_path, 'data')


@app.route("/")
def landing():
    return render_template("landing.html", **fatten(resume_data.get_identification()))


def information():
    if request.method == 'POST':
        resume_data.update_identification(request.form)
    return render_template("information.html", **fatten(resume_data.get_identification()))


@app.route("/summary", methods=["GET", "POST"])
def summary():
    if request.method == 'POST':
        resume_data.update_summary(request.form)
    return render_template("information.html", **fatten(resume_data.get_summary()))
@app.route("/education", methods=["GET", "POST"])
def education():
    if request.method == 'POST':
        resume_data.update_education(request.form)
    return render_template("education.html", **fatten(resume_data.get_education()))


@app.route("/certifications", methods=["GET", "POST"])
def certifications():
    if request.method == 'POST':
        resume_data.update_certifications(request.form)
    return render_template("certifications.html", **fatten(resume_data.get_certifications()))


@app.route("/skills", methods=["GET", "POST"])
def skills():
    if request.method == 'POST':
        resume_data.update_skills(request.form)
    return render_template("skills.html", **fatten(resume_data.get_skills()))


@app.route("/employment", methods=["GET", "POST"])
def positions():
    if request.method == 'POST':
        resume_data.update_positions(request.form)
    return render_template("employment.html", **fatten(resume_data.get_positions()))


@app.route("/achievements", methods=["GET", "POST"])
def achievements():
    return render_template("achievements.html", **fatten(resume_data.get_achievements()))


@app.route("/glossary", methods=["GET", "POST"])
def glossary():
    if request.method == 'POST':
        resume_data.update_glossary(request_form)
    return render_template("glossary.html", **fatten(resume_data.get_glossary()))


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
    app.run(debug=True)
