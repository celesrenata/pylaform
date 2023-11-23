from pylaform.utilities.dbCommands import Queries
from flask import Flask, render_template, request
from pylaform.utilities.commands import flatten

app = Flask(__name__,
            static_url_path="",
            static_folder="pylaform/static",
            template_folder="pylaform/templates")

resume_data = Queries()


@app.route("/")
def landing():
    return render_template("landing.html", **flatten(resume_data.get_identification()))


@app.route("/information", methods=["GET", "POST"])
def information():
    if request.method == 'POST':
        resume_data.update_identification(request.form)
    return render_template("information.html", **flatten(resume_data.get_identification()))


@app.route("/education", methods=["GET", "POST"])
def education():
    return render_template("education.html", **flatten(resume_data.get_education()))


@app.route("/certifications", methods=["GET", "POST"])
def certifications():
    return render_template("certifications.html", **flatten(resume_data.get_certifications()))


@app.route("/skills", methods=["GET", "POST"])
def skills():
    return render_template("skills.html", **flatten(resume_data.get_skills()))


@app.route("/employment", methods=["GET", "POST"])
def employment():
    return render_template("employment.html", **flatten(resume_data.get_positions()))


@app.route("/achievements", methods=["GET", "POST"])
def achievements():
    return render_template("achievements.html", **flatten(resume_data.get_achievements()))


@app.route("/glossary", methods=["GET", "POST"])
def glossary():
    return render_template("glossary.html", **flatten(resume_data.get_glossary()))


if __name__ == '__main__':
    app.run(debug=True)

# def main():
#     """
#     Pylaform is a resume generator backed by mariadb
#     :return: None
#     """
#
#     args = argument_parser()
#
#     match str(args.template):
#         case "one-page":
#             generator = onePage.Generator()
#             generator.run()
#         case "hybrid":
#             generator = hybrid.Generator()
#             generator.run()
#         case "chronological":
#             # generator = onePager.Generator()
#             # generator.run()
#             print("Coming Soon!")
#         case "functional":
#             # generator = onePager.Generator()
#             # generator.run()
#             print("Coming Soon!")
#         case _:
#             print("Run --help argument for options")
#
#
 # if __name__ == "__main__":
     # main()

