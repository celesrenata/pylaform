from flask import Flask, render_template, request, send_from_directory
import os
from pylaform.commands.db.query import Get
from pylaform.commands.db.update import Post
from pylaform.latex_templates import hybrid, onePage
from pylaform.utilities.commands import fatten, listify

app = Flask(__name__,
            static_url_path="",
            static_folder="pylaform/static",
            template_folder="pylaform/templates")

# Not currently used.
app.jinja_env.add_extension('jinja2.ext.do')

resume_query = Get()
resume_update = Post()
uploads = os.path.join(app.root_path, 'data')


@app.route("/")
def landing():
    return render_template("landing.html", **fatten(resume_query.get_identification()))


@app.route("/information", methods=["GET", "POST"])
def information():
    if request.method == 'POST':
        resume_update.update_identification(request.form)
        resume_query.purge_cache("identification")
    return render_template("information.html", **fatten(resume_query.get_identification()))


@app.route("/summary", methods=["GET", "POST"])
def summary():
    if request.method == 'POST':
        resume_update.update_summary(request.form)
        resume_query.purge_cache("summary")
    return render_template("summary_index.html", **fatten(resume_query.get_summary()))

@app.route("/education", methods=["GET", "POST"])
def education():
    if request.method == 'POST':
        resume_update.update_education(request.form)
        resume_query.purge_cache("education")
    return render_template("education_index.html", **fatten(resume_query.get_education()))


@app.route("/certifications", methods=["GET", "POST"])
def certifications():
    if request.method == 'POST':
        resume_update.update_certifications(request.form)
        resume_query.purge_cache("certificaitons")
    return render_template("certifications_index.html", **fatten(resume_query.get_certifications()))


@app.route("/skills", methods=["GET", "POST"])
def skills():
    if request.method == 'POST':
        resume_update.update_skills(request.form)
        resume_query.purge_cache()
    return render_template("skills_index.html", **fatten(resume_query.get_skills()))


@app.route("/employment", methods=["GET", "POST"])
def positions():
    if request.method == 'POST':
        resume_update.update_positions(request.form)
        resume_query.purge_cache("positions")
    return render_template("employment_index.html", **fatten(resume_query.get_positions()))


@app.route("/achievements", methods=["GET", "POST"])
def achievements():
    if request.method == 'POST':
        resume_update.update_achievements(request.form)
        resume_query.purge_cache("achievements")
    return render_template("achievements_index.html", **fatten(resume_query.get_achievements()))


@app.route("/glossary", methods=["GET", "POST"])
def glossary():
    if request.method == 'POST':
        resume_update.update_glossary(request.form)
        resume_query.purge_cache("glossary")
    return render_template("glossary_index.html", **fatten(resume_query.get_glossary()))


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
