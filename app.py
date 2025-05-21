from datetime import datetime
from flask import jsonify as flask_jsonify
from pylaform.database.templateWorker import Worker
from datetime import timedelta
import boto3
import json
import os
import sys
from flask import Flask, Blueprint, render_template, request, redirect, url_for, flash, session
from pylaform.database.connect import db, create_user_identification
from pylaform.auth import (
    create_user, create_session, login_required, verify_password,
    validate_password, password_strength_message, send_password_reset_email,
    store_reset_token, verify_reset_token, invalidate_reset_token,
    update_user_password, invalidate_all_sessions, get_user_by_email
)
from pylaform.services.resumeManager import ResumeManager

import time
import secrets
import logging

# Set up logging for the whole app
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Ensure logs go to stdout for CloudWatch
    ]
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Explicitly set logger level to DEBUG

# Create the resume blueprint
resume_bp = Blueprint('resume', __name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FOLDER = os.path.join(BASE_DIR, 'templates')
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')


def get_secret_key():
    """
    Returns the Flask secret key.
    - In AWS Lambda, tries to load from AWS Secrets Manager (pylaform/flask-secret).
    - Otherwise, uses the SECRET_KEY environment variable, or falls back to a dev key.
    """
    if 'AWS_LAMBDA_FUNCTION_NAME' in os.environ:
        try:
            secret_name = "pylaform/flask-secret"
            region_name = os.environ.get("AWS_REGION", "us-west-2")
            client = boto3.client('secretsmanager', region_name=region_name)
            get_secret_value_response = client.get_secret_value(SecretId=secret_name)
            secret = json.loads(get_secret_value_response['SecretString'])
            return secret['FLASK_SECRET_KEY']
        except Exception as e:
            print(f"WARNING: Could not load Flask secret from Secrets Manager: {e}")
            raise RuntimeError("Flask secret key not found in Secrets Manager and no fallback provided.")
    else:
        # Local development
        return os.environ.get('SECRET_KEY', 'dev-secret-key')

app = Flask(
    __name__,
    template_folder=TEMPLATE_FOLDER,
    static_folder=STATIC_FOLDER
)
app.secret_key = get_secret_key()
# Recommended security settings
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

@resume_bp.route('/resume-management', methods=['GET'])
@login_required
def resume_management():
    """
    Route handler for the Resume Management page.
    """
    try:
        # Get user_id from session
        user_id = session.get('user_id')
        logger.info(f"User ID from session: {user_id}")

        manager = ResumeManager(user_id)
        logger.info("ResumeManager initialized")

        # Get all resumes and active resume ID
        resumes = manager.get_all_resumes()
        logger.info(f"Retrieved resumes: {resumes}")

        active_resume_id = manager.get_active_resume_id()
        logger.info(f"Active resume ID: {active_resume_id}")

        return render_template(
            "resume_management.html",
            resumes=resumes,
            active_resume_id=active_resume_id
        )
    except Exception as e:
        logger.error(f"Error in resume management route: {str(e)}")
        logger.exception("Detailed traceback:")  # This will log the full traceback
        flash(f"Error loading resume management: {str(e)}", "danger")
        # Use absolute URL instead of url_for
        return redirect('/')


@resume_bp.route('/create-resume', methods=['POST'])
@login_required
def create_resume():
    """
    Create a new resume for the current user.
    """
    try:
        user_id = session.get('user_id')
        name = request.form.get('resume_name', '').strip()

        if not name:
            flash("Resume name is required", "warning")
            return redirect(url_for('resume.resume_management'))

        manager = ResumeManager(user_id)
        resume_id = manager.create_resume(name)

        if resume_id:
            flash(f"Resume '{name}' created successfully", "success")
        else:
            flash("Failed to create resume", "danger")
        return redirect(url_for('resume.resume_management'))
    except Exception as e:
        logger.error(f"Error creating resume: {str(e)}")
        flash(f"Error creating resume: {str(e)}", "danger")
        return redirect(url_for('resume.resume_management'))


@resume_bp.route('/rename-resume', methods=['POST'])
@login_required
def rename_resume():
    """
    Rename an existing resume.
    """
    try:
        user_id = session.get('user_id')
        resume_id = request.form.get('resume_id')
        new_name = request.form.get('resume_name', '').strip()

        if not resume_id or not new_name:
            flash("Resume ID and new name are required", "warning")
            return redirect(url_for('resume.resume_management'))

        manager = ResumeManager(user_id)
        success = manager.rename_resume(resume_id, new_name)

        if success:
            flash(f"Resume renamed to '{new_name}' successfully", "success")
        else:
            flash("Failed to rename resume", "danger")
        return redirect(url_for('resume.resume_management'))
    except Exception as e:
        logger.error(f"Error renaming resume: {str(e)}")
        flash(f"Error renaming resume: {str(e)}", "danger")
        return redirect(url_for('resume.resume_management'))


@resume_bp.route('/delete-resume', methods=['POST'])
@login_required
def delete_resume():
    """
    Delete an existing resume.
    """
    try:
        user_id = session.get('user_id')
        resume_id = request.form.get('resume_id')

        if not resume_id:
            flash("Resume ID is required", "warning")
            return redirect(url_for('resume.resume_management'))

        manager = ResumeManager(user_id)
        success = manager.delete_resume(resume_id)

        if success:
            flash("Resume deleted successfully", "success")
        else:
            flash("Failed to delete resume", "danger")
        return redirect(url_for('resume.resume_management'))
    except Exception as e:
        logger.error(f"Error deleting resume: {str(e)}")
        flash(f"Error deleting resume: {str(e)}", "danger")
        return redirect(url_for('resume.resume_management'))

@resume_bp.route('/set-active-resume', methods=['POST'])
@login_required
def set_active_resume():
    """
    Set a resume as the active resume for the current user.
    """
    try:
        user_id = session.get('user_id')
        resume_id = request.form.get('resume_id')

        if not resume_id:
            flash("Resume ID is required", "warning")
            return redirect(url_for('resume.resume_management'))

        manager = ResumeManager(user_id)
        success = manager.set_active_resume(resume_id)

        if success:
            flash("Active resume updated successfully", "success")
        else:
            flash("Failed to update active resume", "danger")
        return redirect(url_for('resume.resume_management'))
    except Exception as e:
        logger.error(f"Error setting active resume: {str(e)}")
        flash(f"Error setting active resume: {str(e)}", "danger")
        return redirect(url_for('resume.resume_management'))


@resume_bp.route('/copy-resume', methods=['POST'])
@login_required
def copy_resume():
    """
    Copy an existing resume with a new name
    """
    logger.debug("Entering copy_resume route handler")
    try:
        user_id = session.get('user_id')
        logger.debug(f"User ID from session: {user_id}")

        # Log all form data for debugging
        logger.debug(f"All form data: {request.form}")

        resume_id = request.form.get('resume_id')
        resume_name = request.form.get('resume_name')
        make_active = 'make_active' in request.form

        logger.debug(f"Form data - resume_id: {resume_id}, resume_name: {resume_name}, make_active: {make_active}")
        logger.info(f"Copy resume request: ID={resume_id}, Name={resume_name}, MakeActive={make_active}")

        if not resume_id or not resume_name:
            logger.warning("Missing required parameters: resume_id or resume_name")
            flash("Resume ID and name are required", "danger")
            return redirect(url_for('resume.resume_management'))

        logger.debug("Initializing ResumeManager")
        manager = ResumeManager(user_id)

        logger.debug(f"Calling manager.copy_resume with params: {resume_id}, {resume_name}, {make_active}")
        success = manager.copy_resume(resume_id, resume_name, make_active)
        logger.debug(f"Copy resume operation result: {success}")

        if success:
            logger.info(f"Successfully copied resume '{resume_name}'")
            flash(f"Resume '{resume_name}' copied successfully", "success")
        else:
            logger.error("Failed to copy resume - manager.copy_resume returned False")
            flash("Failed to copy resume", "danger")

        logger.debug("Redirecting to resume management page")
        return redirect(url_for('resume.resume_management'))
    except Exception as e:
        logger.error(f"Error copying resume: {str(e)}")
        logger.exception("Detailed traceback:")  # This will log the full traceback
        flash(f"Error copying resume: {str(e)}", "danger")
        return redirect(url_for('resume.resume_management'))

# Add this inside your resume blueprint routes in app.py

@resume_bp.route('/switch-resume', methods=['POST'])
@login_required
def switch_resume():
    """
    Handle switching the active resume based on user selection.
    Returns to the specified page after switching.
    """
    try:
        user_id = session.get('user_id')
        resume_id = request.form.get('resume_id')
        return_to = request.form.get('return_to', 'resume.resume_management')

        logger.debug(f"Switch resume request: resume_id={resume_id}, return_to={return_to}")

        if not resume_id:
            flash("Please select a resume", "warning")
            return redirect_to_return_page(return_to)

        manager = ResumeManager(user_id)
        success = manager.set_active_resume(resume_id)

        if success:
            # Update the active resume in the session
            session['active_resume_id'] = resume_id
            flash("Active resume updated", "success")
        else:
            flash("Failed to update active resume", "danger")

    except Exception as e:
        logger.error(f"Error switching resume: {str(e)}")
        logger.exception("Detailed traceback:")  # This will log the full traceback
        flash("An error occurred while switching resumes", "danger")
        return_to = 'resume.resume_management'  # Default fallback

    return redirect_to_return_page(return_to)


def redirect_to_return_page(return_to):
    """
    Helper function to handle redirects with proper blueprint prefixes.
    """
    logger.debug(f"Attempting to redirect to: {return_to}")

    # Try to redirect using url_for first
    try:
        return redirect(url_for(return_to))
    except Exception as e:
        logger.debug(f"url_for failed with: {str(e)}")

        # If return_to is not a valid endpoint, try it as a direct path
        try:
            # Handle blueprint routes - if it's a simple name like 'summary',
            # it's likely a blueprint route that needs the prefix
            if not return_to.startswith('/') and '.' not in return_to:
                # This is likely a blueprint route without the blueprint name
                path = f'/resume/{return_to}'
                logger.debug(f"Treating as blueprint route: {path}")
                return redirect(path)
            else:
                # Use as-is if it starts with a slash, otherwise add one
                path = return_to if return_to.startswith('/') else f'/{return_to}'
                logger.debug(f"Using direct path: {path}")
                return redirect(path)
        except Exception as e:
            logger.error(f"Direct path redirect failed: {str(e)}")
            # If all else fails, go to resume management
            logger.error(f"Failed to redirect to '{return_to}', falling back to resume management")
            return redirect(url_for('resume.resume_management'))

@app.route('/')
def index():
    # Check if user is logged in
    user_id = session.get('user_id')

    # Initialize context with default values
    context = {
        'user_id': user_id,
        'identification': None,
        'is_authenticated': user_id is not None
    }

    if user_id:
        try:
            # Initialize the worker with the user's ID
            worker = Worker(user_id)

            # Check if the user has identification data
            identification = worker.get_identification()

            # If no identification data exists, create default identification
            if not identification:
                logger.info(f"No identification found for user {user_id}, creating defaults")
                worker.create_default_identification()
                # Fetch the newly created identification data
                identification = worker.get_identification()

            # Add identification data to context
            context['identification'] = identification

        except Exception as e:
            logger.error(f"Error in index route: {str(e)}")
            flash("An error occurred while loading your profile data", "error")

    # Render the template with the context
    return render_template("index.html", **context)

@app.route("/landing")
@login_required
def landing():
    """
    Route handler for the homepage.
    """
    return render_template("landing.html")


# Example snippet from your information route handler

@resume_bp.route('/information', methods=['GET', 'POST'])
@login_required
def information():
    try:
        user_id = session.get('user_id')
        resume_manager = ResumeManager(user_id)
        worker = Worker(user_id)

        # Get all resumes and determine active resume
        all_resumes = resume_manager.get_all_resumes()
        active_resume_id = resume_manager.get_active_resume_id()
        session['active_resume_id'] = active_resume_id  # Keep session in sync

        # Handle resume switch from dropdown
        if request.method == 'POST' and 'resume_id' in request.form:
            new_resume_id = request.form['resume_id']
            resume_manager.set_active_resume(new_resume_id)
            session['active_resume_id'] = new_resume_id
            return redirect(url_for('resume.information'))

        # Handle AJAX form submission for contact info
        if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            form_data = request.form.to_dict()
            form_data['active_resume_id'] = active_resume_id
            success = worker.process_information_form(form_data, resume_id=active_resume_id)
            if success:
                return '', 200
            else:
                return '', 400

        # Load contact info for the active resume
        payload = worker.get_identification_safely(resume_id=active_resume_id)

        # Define the desired order of attributes
        attr_order = [
            "name", "email", "phone", "location", "www", "linkedin", "github"
        ]
        # Sort payload by this order; unknown attrs go last
        payload_sorted = sorted(
            payload,
            key=lambda x: attr_order.index(x.get("attr", "")) if x.get("attr", "") in attr_order else len(attr_order)
        )

        return render_template(
            'information.html',
            all_resumes=all_resumes,
            active_resume_id=active_resume_id,
            payload=payload_sorted,
            debug=app.debug
        )
    except Exception as e:
        logger.error(f"Error in information route: {str(e)}")
        flash(f"An error occurred: {str(e)}", "danger")
        return render_template('information.html', all_resumes=[], active_resume_id=None, payload=[], debug=app.debug)

# Add more route handlers for other pages referenced in your HTML
@resume_bp.route('/summary', methods=['GET', 'POST'])
@login_required
def summary():
    try:
        # Import Worker
        user_id = session.get('user_id')
        worker = Worker(user_id)

        # Get the active resume ID and name
        resume_manager = ResumeManager(user_id)
        active_resume_id = session.get('active_resume_id')
        if not active_resume_id:
            active_resume_id = resume_manager.get_active_resume_id()
            if active_resume_id:
                session['active_resume_id'] = active_resume_id

        # Get all resumes for the dropdown
        all_resumes = resume_manager.get_all_resumes()

        active_resume = resume_manager.get_resume(active_resume_id) if active_resume_id else None
        active_resume_name = active_resume.get('name', 'Default Resume') if active_resume else 'Default Resume'

        # Handle form submissions
        if request.method == 'POST':
            form_data = request.form
            logger.debug(f"Received form data: {dict(form_data)}")

            # Check for deletion
            if '_delete' in form_data:
                delete_id = form_data.get('_delete')
                logger.debug(f"Delete request for ID: {delete_id}")
                if delete_id:
                    # Make sure we're using the correct resume_id
                    resume_id = form_data.get('active_resume_id', active_resume_id)
                    logger.debug(f"Deleting summary {delete_id} from resume {resume_id}")

                    # Call delete_entry with the correct parameters
                    success = worker.delete_entry("summary", delete_id, resume_id=resume_id)
                    logger.debug(f"Delete operation result: {success}")

                    if success:
                        flash("Summary point deleted successfully.", "success")
                    else:
                        flash("Failed to delete summary point.", "danger")

                    return redirect(url_for('resume.summary'))

            # Process updates for existing summaries
            updates_made = False
            for key in form_data:
                # Look for existing items (UUID format)
                if '_shortdesc' in key and not key.startswith('new_'):
                    summary_id = key.split('_')[0]
                    if len(summary_id) == 36:  # UUID length
                        shortdesc = form_data.get(f"{summary_id}_shortdesc", "")
                        longdesc = form_data.get(f"{summary_id}_longdesc", "")
                        summaryorder = form_data.get(f"{summary_id}_summaryorder", "99")

                        # Convert summaryorder to integer
                        try:
                            summaryorder = int(summaryorder)
                        except (ValueError, TypeError):
                            summaryorder = 99

                        # Update the summary
                        success = worker.update_summary(
                            summary_id,
                            resume_id=active_resume_id,
                            shortdesc=shortdesc,
                            longdesc=longdesc,
                            summaryorder=summaryorder
                        )

                        if success:
                            updates_made = True
                            logger.debug(f"Updated summary {summary_id}")
                        else:
                            logger.error(f"Failed to update summary {summary_id}")

            # Process new summaries - handle array format
            new_shortdescs = form_data.getlist('new_shortdesc')
            new_longdescs = form_data.getlist('new_longdesc')
            new_summaryorders = form_data.getlist('new_summaryorder')

            # Make sure we have the same number of items in each list
            min_length = min(len(new_shortdescs), len(new_longdescs), len(new_summaryorders))

            for i in range(min_length):
                shortdesc = new_shortdescs[i].strip()
                longdesc = new_longdescs[i].strip()

                # Skip empty entries
                if not shortdesc and not longdesc:
                    continue

                # Convert summaryorder to integer
                try:
                    summaryorder = int(new_summaryorders[i])
                except (ValueError, TypeError, IndexError):
                    summaryorder = 99

                # Add the new summary
                result = worker.add_summary(
                    shortdesc=shortdesc,
                    longdesc=longdesc,
                    summaryorder=summaryorder,
                    resume_id=active_resume_id
                )

                if result:
                    updates_made = True
                    logger.debug(f"Added new summary with ID {result}")
                else:
                    logger.error("Failed to add new summary")

            if updates_made:
                flash("Summary updated successfully.", "success")

            return redirect(url_for('resume.summary'))

        # GET request - display the form
        payload = worker.get_summary(resume_id=active_resume_id)
        logger.debug(f"Retrieved {len(payload)} summaries")

        return render_template(
            'summary_index.html',
            payload=payload,
            all_resumes=all_resumes,
            active_resume_id=active_resume_id,
            active_resume_name=active_resume_name
        )
    except Exception as e:
        logger.error(f"Error in summary route: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        flash("An error occurred while processing your request.", "danger")
        return redirect(url_for('resume.dashboard'))

@resume_bp.route("/education", methods=['GET'])
@login_required
def education():
    user_id = session.get('user_id')
    worker = Worker(user_id)
    resume_manager = ResumeManager(user_id)

    try:
        # Get all resumes and determine active resume
        all_resumes = resume_manager.get_all_resumes()
        active_resume_id = session.get('active_resume_id')
        if not active_resume_id:
            active_resume_id = resume_manager.get_active_resume_id()
            if active_resume_id:
                session['active_resume_id'] = active_resume_id

        # GET request - display the form
        schools = worker.get_all_education(resume_id=active_resume_id)
        logger.debug(f"Retrieved {len(schools)} schools for user {user_id}")

        return render_template(
            "education_index.html",
            payload=schools,
            all_resumes=all_resumes,
            active_resume_id=active_resume_id
        )
    except Exception as e:
        logger.error(f"Error in education route: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        flash("An error occurred while loading education information.", "danger")
        return redirect(url_for('landing'))  # Change this to an existing route


@resume_bp.route('/education', methods=['POST'])
@login_required
def education_post():
    user_id = session.get('user_id')
    worker = Worker(user_id)
    resume_manager = ResumeManager(user_id)

    form_data = request.form.to_dict()
    logger.debug(f"Received education form data: {form_data}")

    active_resume_id = form_data.get('active_resume_id')
    if not active_resume_id:
        active_resume_id = session.get('active_resume_id')
        if not active_resume_id:
            active_resume_id = resume_manager.get_active_resume_id()
            if active_resume_id:
                session['active_resume_id'] = active_resume_id

    try:
        # Handle deletions
        if "_delete" in form_data:
            delete_id = form_data.get("_delete")
            logger.debug(f"Processing delete request for school ID: {delete_id}")
            if delete_id and not delete_id.startswith("new"):
                success = worker.delete_entry("school", delete_id, resume_id=active_resume_id)
                logger.debug(f"Delete operation result: {success}")
                if success:
                    flash("School deleted successfully", "success")
                else:
                    flash("Failed to delete school", "danger")
            return redirect(url_for("resume.education"))

        # Process updates and new additions
        school_data = {}
        focus_data = {}
        achievement_data = {}

        for key, value in form_data.items():
            logger.debug(f"Processing form key: {key}, value: {value}")
            if "_" in key:
                parts = key.split("_", 1)
                school_id = parts[0]

                if "focus_" in key:
                    if school_id not in focus_data:
                        focus_data[school_id] = []
                    focus_parts = key.split("_focus_")
                    if len(focus_parts) > 1:
                        focus_index = focus_parts[1]
                        focus_data[school_id].append({
                            "index": focus_index,
                            "description": value
                        })
                elif "achievement_" in key:
                    if school_id not in achievement_data:
                        achievement_data[school_id] = []
                    achievement_parts = key.split("_achievement_")
                    if len(achievement_parts) > 1:
                        achievement_index = achievement_parts[1]
                        achievement_data[school_id].append({
                            "index": achievement_index,
                            "description": value
                        })
                else:
                    field = parts[1]
                    if school_id not in school_data:
                        school_data[school_id] = {}
                    school_data[school_id][field] = value

        logger.debug(f"Processed school data: {school_data}")
        logger.debug(f"Processed focus data: {focus_data}")
        logger.debug(f"Processed achievement data: {achievement_data}")

        for school_id, data in school_data.items():
            enabled = "enabled" in data
            data["state"] = 1 if enabled else 0
            data.pop("enabled", None)
            data.pop("rowid", None)

            if school_id.startswith("new"):
                if "name" in data:
                    logger.debug(f"Adding new school: {data}")
                    new_school_id = worker.add_school(
                        name=data.get("name", ""),
                        location=data.get("location", ""),
                        degree=data.get("degree", ""),
                        graddate=data.get("graddate", ""),
                        resume_id=active_resume_id
                    )
                    logger.debug(f"New school added with ID: {new_school_id}")
                    if new_school_id:
                        if school_id in focus_data:
                            for focus in focus_data[school_id]:
                                if focus["description"].strip():
                                    worker.add_focus(new_school_id, focus["description"], resume_id=active_resume_id)
                        if school_id in achievement_data:
                            for achievement in achievement_data[school_id]:
                                if achievement["description"].strip():
                                    worker.add_achievement(new_school_id, achievement["description"], resume_id=active_resume_id)
                    else:
                        logger.error(f"Failed to add new school: {data}")
                        flash("Failed to add new school", "danger")
            else:
                data.pop('resume_id', None)
                logger.debug(f"Updating school: school_id={school_id}, resume_id={active_resume_id}, data={data}")
                result = worker.update_school(school_id, resume_id=active_resume_id, **data)
                logger.debug(f"update_school result: {result}")

                if result:
                    if school_id in focus_data:
                        for focus in focus_data[school_id]:
                            if focus["description"].strip():
                                worker.update_focus(school_id, focus["index"], focus["description"], resume_id=active_resume_id)
                    if school_id in achievement_data:
                        for achievement in achievement_data[school_id]:
                            if achievement["description"].strip():
                                worker.update_achievement(school_id, achievement["index"], achievement["description"], resume_id=active_resume_id)
                else:
                    logger.error(f"Failed to update school: {school_id}")
                    flash(f"Failed to update school {data.get('name', '')}", "danger")

        flash("Education information updated successfully", "success")
    except Exception as e:
        logger.error(f"Error in education_post: {str(e)}")
        flash("An error occurred while updating education information", "danger")

    return redirect(url_for("resume.education"))

@app.route('/certifications', methods=['GET', 'POST'])
@login_required
def certifications():
    print("DEBUG: Beginning certifications route handler")
    try:
        # Import Worker
        user_id = session.get('user_id')
        worker = Worker(user_id)

        # Handle form submissions
        if request.method == 'POST':
            print("DEBUG: Processing POST request for certifications")
            form_data = request.form
            print(f"DEBUG: Form data: {form_data}")

            certifications = worker.get_all_certifications()
            print(f"DEBUG: Retrieved {len(certifications)} certifications for display")

            # Check for deletion
            if '_delete' in form_data:
                delete_id = form_data.get('_delete')
                print(f"DEBUG: Delete request for certification {delete_id}")
                if delete_id:
                    success = worker.delete_entry("certification", delete_id)
                    print(f"DEBUG: Delete result: {success}")
                    # Redirect to avoid resubmission
                    return redirect(url_for('certifications'))

            # Process updates first
            updates_made = False
            for key, value in form_data.items():
                # Look for existing items (not starting with "new")
                if "_name" in key and not key.startswith("new"):
                    item_id = key.split("_")[0]
                    name = value
                    authority = form_data.get(f"{item_id}_authority", "")
                    date_achieved = form_data.get(f"{item_id}_date_achieved", "")
                    expiration_date = form_data.get(f"{item_id}_expiration_date", "")

                    # Check if there's an order value
                    cert_order = form_data.get(f"{item_id}_certorder", 99)
                    try:
                        cert_order = int(cert_order)
                    except:
                        cert_order = 99

                    print(f"DEBUG: Updating certification {item_id}")
                    update_data = {
                        "name": name,
                        "authority": authority,
                        "date_achieved": date_achieved,
                        "certorder": cert_order
                    }

                    # Only include expiration date if it exists
                    if expiration_date:
                        update_data["expiration_date"] = expiration_date

                    success = worker.update_certification(item_id, **update_data)
                    if success:
                        updates_made = True

            # Process new items (starting with "new")
            for key, value in form_data.items():
                if "_name" in key and key.startswith("new"):
                    new_id = key.split("_")[0]  # Extract "new1", "new2", etc.
                    name = value
                    authority = form_data.get(f"{new_id}_authority", "")
                    date_achieved = form_data.get(f"{new_id}_date_achieved", "")
                    expiration_date = form_data.get(f"{new_id}_expiration_date", "")

                    # Check if there's content to add
                    if name.strip() and authority.strip() and date_achieved.strip():
                        print(f"DEBUG: Adding new certification {name}")
                        success = worker.add_certification(
                            name=name,
                            authority=authority,
                            date_achieved=date_achieved,
                            expiration_date=expiration_date if expiration_date.strip() else None
                        )
                        if success:
                            updates_made = True

            # Redirect to avoid resubmission
            if updates_made:
                return redirect(url_for('certifications'))

        # Get certifications
        certifications = worker.get_all_certifications()
        print(f"DEBUG: Retrieved {len(certifications)} certifications for display")

        # Transform the data to match template expectations
        transformed_certifications = []
        for cert in certifications:
            transformed_certifications.append({
                "id": cert.get('SK'),  # Use SK as id
                "name": cert.get('name', ''),
                "authority": cert.get('authority', ''),
                "date_achieved": cert.get('date_achieved', ''),
                "expiration_date": cert.get('expiration_date', ''),
                "state": cert.get('state', 1),
                "certorder": cert.get('certorder', 99)
            })

        # Sort by certification order
        transformed_certifications.sort(key=lambda x: int(x.get('certorder', 99)))

        print(f"DEBUG: Rendering template with {len(transformed_certifications)} transformed certifications")
        return render_template('certifications_index.html', payload=transformed_certifications)

    except Exception as e:
        import traceback
        print(f"DEBUG: Exception in certifications route: {str(e)}")
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        return f"Error: {str(e)}", 500


@app.route("/employment", methods=["GET", "POST"])
@login_required
def employment():
    # Initialize worker
    user_id = session.get('user_id')
    worker = Worker(user_id)

    if request.method == "POST":
        # Process form data
        form_data = request.form.to_dict()
        print(f"DEBUG: Employment POST with {len(form_data)} form fields")
        print(f"DEBUG: Form field keys: {sorted(list(form_data.keys()))}")

        # Handle achievement deletion
        if "_delete_achievement" in form_data:
            achievement_id = form_data.get("_delete_achievement")
            print(f"DEBUG: Processing achievement deletion request for ID: {achievement_id}")

            if achievement_id and not achievement_id.startswith("new-achievement-"):
                # Remove any prefix if it exists
                if achievement_id.startswith("achievement_"):
                    achievement_id = achievement_id[12:]  # Remove "achievement_" prefix

                success = worker.delete_entry("achievement", achievement_id)
                print(f"DEBUG: Achievement deletion result: {success}")
                if success:
                    flash("Achievement deleted successfully", "success")
                else:
                    flash("Error deleting achievement", "danger")

            return redirect(url_for("employment"))

        # Handle position deletion
        if "_delete_position" in form_data:
            position_id = form_data.get("_delete_position")
            print(f"DEBUG: Processing position deletion request for ID: {position_id}")

            if position_id and not position_id.startswith("new-position-"):
                # Remove any prefix if it exists
                if position_id.startswith("position_"):
                    position_id = position_id[9:]  # Remove "position_" prefix

                success = worker.delete_entry("position", position_id)
                print(f"DEBUG: Position deletion result: {success}")
                if success:
                    flash("Position deleted successfully", "success")
                else:
                    flash("Error deleting position", "danger")

            return redirect(url_for("employment"))

        # Handle employer deletion
        if "_delete_employer" in form_data:
            employer_id = form_data.get("_delete_employer")
            print(f"DEBUG: Processing employer deletion request for ID: {employer_id}")

            if employer_id and not employer_id.startswith("new"):
                # Remove any prefix if it exists
                if employer_id.startswith("employer_"):
                    employer_id = employer_id[9:]  # Remove "employer_" prefix

                # First, get all positions for this employer
                positions = worker.query.get_related_items("employer", employer_id, "position", False)
                print(f"DEBUG: Found {len(positions)} positions to delete for employer {employer_id}")

                # Delete all positions first
                for position in positions:
                    position_id = position.get("SK")
                    worker.delete_entry("position", position_id)
                    print(f"DEBUG: Deleted position {position_id}")

                # Then delete the employer
                success = worker.delete_entry("employer", employer_id)
                print(f"DEBUG: Employer deletion result: {success}")

                if success:
                    flash("Employer and all associated positions deleted successfully", "success")
                else:
                    flash("Error deleting employer", "danger")

            return redirect(url_for("employment"))

        # Process employers first
        # Keep track of new employers with their temporary IDs
        new_employer_map = {}  # Maps temporary ID to real DB ID

        # First, process all employer entries (existing and new)
        for key in form_data:
            if key.startswith("employer_") and "_name" in key:
                # Extract employer ID and check if it's new
                parts = key.split("_", 2)
                employer_id = parts[1]

                print(f"DEBUG: Processing employer with ID: {employer_id}")

                # Get employer data fields
                name = form_data.get(f"employer_{employer_id}_name", "").strip()
                location = form_data.get(f"employer_{employer_id}_location", "").strip()
                enabled = f"employer_{employer_id}_enabled" in form_data

                # Skip empty employers
                if not name:
                    print(f"DEBUG: Skipping empty employer: {employer_id}")
                    continue

                # Check if this is a new or existing employer
                is_new = employer_id.startswith("new")

                if is_new:
                    # Add new employer to database
                    print(f"DEBUG: Adding new employer: {name}")
                    new_id = worker.add_employer(name=name, location=location)
                    if new_id:
                        print(f"DEBUG: Added employer successfully, got DB ID: {new_id}")
                        # Store mapping of temporary ID to real DB ID
                        new_employer_map[f"employer_{employer_id}"] = new_id
                    else:
                        print(f"DEBUG: Failed to add employer {name}")
                else:
                    # Update existing employer
                    print(f"DEBUG: Updating employer: {employer_id}")
                    success = worker.update_employer(
                        employer_id,
                        name=name,
                        location=location,
                        state=1 if enabled else 0
                    )
                    print(f"DEBUG: Update result: {success}")

        # Track new position IDs for potential new achievements
        new_position_ids = {}  # Maps temporary ID to real DB ID

        # Now process positions
        for key in form_data:
            # Check for new position fields (new-position format)
            if key.startswith("new-position-") and "_title" in key:
                # Extract position ID from key
                parts = key.split("_", 1)
                position_temp_id = parts[0]  # e.g., "new-position-1"

                print(f"DEBUG: Processing new position: {position_temp_id}")

                # Get position data
                title = form_data.get(f"{position_temp_id}_title", "").strip()
                startdate = form_data.get(f"{position_temp_id}_startdate", "").strip()

                # Check for current position checkbox
                is_current = f"{position_temp_id}_current" in form_data
                enddate = None if is_current else form_data.get(f"{position_temp_id}_enddate", "").strip()

                # Get the employer ID - crucial part
                employer_ref = form_data.get(f"{position_temp_id}_employer_id", "")
                print(f"DEBUG: Position references employer: {employer_ref}")

                # Skip positions with missing required data
                if not title or not startdate:
                    print(f"DEBUG: Skipping position with missing data - Title: '{title}', Start date: '{startdate}'")
                    continue

                # If employer_ref refers to a new employer, map to real ID
                real_employer_id = employer_ref
                if employer_ref in new_employer_map:
                    real_employer_id = new_employer_map[employer_ref]
                    print(f"DEBUG: Mapped temp employer ID {employer_ref} to real ID {real_employer_id}")
                elif employer_ref.startswith("employer_"):
                    real_employer_id = employer_ref.replace("employer_", "")
                    print(f"DEBUG: Extracted employer ID from {employer_ref} to {real_employer_id}")

                # Add the new position
                print(f"DEBUG: Adding position '{title}' to employer '{real_employer_id}'")
                print(f"DEBUG: Position data - Start: {startdate}, End: {enddate}, Current: {is_current}")

                new_position_id = worker.add_position(
                    employer_id=real_employer_id,
                    title=title,
                    startdate=startdate,
                    enddate=enddate,
                    current=is_current
                )

                if new_position_id:
                    print(f"DEBUG: Successfully added position with ID: {new_position_id}")
                    # Store mapping of temporary ID to real DB ID
                    new_position_ids[position_temp_id] = new_position_id
                else:
                    print(f"DEBUG: Failed to add position '{title}'")

            # Handle existing positions (format: position_ID_field)
            elif key.startswith("position_") and "_title" in key:
                # Extract position ID
                parts = key.split("_", 2)
                position_id = parts[1]

                print(f"DEBUG: Processing existing position: {position_id}")

                # Get position data
                title = form_data.get(f"position_{position_id}_title", "").strip()
                startdate = form_data.get(f"position_{position_id}_startdate", "").strip()

                # Check for current position checkbox
                is_current = f"position_{position_id}_current" in form_data
                enddate = None if is_current else form_data.get(f"position_{position_id}_enddate", "").strip()

                # Skip positions with missing required data
                if not title or not startdate:
                    print(
                        f"DEBUG: Skipping position update with missing data - Title: '{title}', Start date: '{startdate}'")
                    continue

                # Update the position
                print(f"DEBUG: Updating position '{title}' (ID: {position_id})")

                update_data = {
                    "title": title,
                    "startdate": startdate,
                    "current": 1 if is_current else 0,
                    "state": 1 if f"position_{position_id}_enabled" in form_data else 0
                }

                if not is_current and enddate:
                    update_data["enddate"] = enddate

                success = worker.update_position(position_id, **update_data)
                print(f"DEBUG: Position update result: {success}")

        # Process achievements with achievement_newach pattern
        for key in form_data:
            if key.startswith("achievement_newach") and key.endswith("_description"):
                # Extract achievement ID (without the _description part)
                achievement_id = key.replace("_description", "")

                # Get achievement data
                description = form_data.get(key, "").strip()
                position_id = form_data.get(f"{achievement_id}_position_id", "").strip()

                print(f"DEBUG: Processing new achievement with ID: {achievement_id}")
                print(f"DEBUG: Description: {description}")
                print(f"DEBUG: Position ID: {position_id}")

                # Skip empty achievements or those without a position
                if not description or not position_id:
                    print(f"DEBUG: Skipping empty achievement or missing position: {achievement_id}")
                    continue

                # If position_id refers to a new position, map to real ID
                real_position_id = position_id
                if position_id in new_position_ids:
                    real_position_id = new_position_ids[position_id]
                    print(f"DEBUG: Mapped temp position ID {position_id} to real ID {real_position_id}")
                elif position_id.startswith("position_"):
                    real_position_id = position_id.replace("position_", "")
                    print(f"DEBUG: Extracted position ID from {position_id} to {real_position_id}")

                # Add new achievement
                print(f"DEBUG: Adding new achievement for position {real_position_id}: {description}")
                new_id = worker.add_achievement(
                    position_id=real_position_id,
                    description=description
                )
                if new_id:
                    print(f"DEBUG: Added achievement successfully, got DB ID: {new_id}")
                else:
                    print(f"DEBUG: Failed to add achievement")

        # Process new achievements - moved outside the position loops to handle all achievements at once
        for key in form_data:
            if key.startswith("new-achievement-") and "_description" in key:
                # Extract achievement temp ID
                achievement_temp_id = key.split("_")[0]  # e.g., "new-achievement-123456"

                # Get achievement data
                description = form_data.get(key, "").strip()
                position_id = form_data.get(f"{achievement_temp_id}_position_id", "").strip()

                print(f"DEBUG: Processing new achievement: {achievement_temp_id}")
                print(f"DEBUG: Description: {description}")
                print(f"DEBUG: Position ID: {position_id}")

                # Skip empty achievements or those without a position
                if not description or not position_id:
                    print(f"DEBUG: Skipping empty achievement or missing position: {achievement_temp_id}")
                    continue

                # If position_id refers to a new position, map to real ID
                real_position_id = position_id
                if position_id in new_position_ids:
                    real_position_id = new_position_ids[position_id]
                    print(f"DEBUG: Mapped temp position ID {position_id} to real ID {real_position_id}")
                elif position_id.startswith("position_"):
                    real_position_id = position_id.replace("position_", "")
                    print(f"DEBUG: Extracted position ID from {position_id} to {real_position_id}")

                # Add new achievement
                print(f"DEBUG: Adding new achievement for position {real_position_id}: {description}")
                new_id = worker.add_achievement(
                    position_id=real_position_id,
                    description=description
                )
                if new_id:
                    print(f"DEBUG: Added achievement successfully, got DB ID: {new_id}")
                else:
                    print(f"DEBUG: Failed to add achievement")

        flash("Employment information updated successfully", "success")
        return redirect(url_for("employment"))

    # GET request - fetch and display data
    employers = worker.get_all_employment()
    return render_template("employment_index.html", payload=employers)


@app.route('/skills', methods=['GET', 'POST'])
@login_required
def skills():
    """
    Route handler for the Skills page.
    """
    try:
        user_id = session.get('user_id')
        worker = Worker(user_id)

        if request.method == 'POST':
            # Check if this is an AJAX request for skill deletion
            if '_delete' in request.form:
                skill_id = request.form.get('_delete')
                if skill_id:
                    success = worker.delete_entry("skill", skill_id)
                    if success:
                        flash("Skill deleted successfully", "success")
                    else:
                        flash("Error deleting skill", "error")
                    return redirect(url_for('skills'))

            # Process the form data
            success, message = worker.process_skills_form(request.form)

            if success:
                flash("Skills updated successfully", "success")
            else:
                flash(f"Error updating skills: {message}", "error")

            return redirect(url_for('skills'))

        # Get all skills for display
        skills = worker.get_all_skills()

        # Group skills by category and subcategory
        categorized_skills = {}
        for skill in skills:
            category = skill.get('category', 'Uncategorized')
            subcategory = skill.get('subcategory', 'General')

            if category not in categorized_skills:
                categorized_skills[category] = {}

            if subcategory not in categorized_skills[category]:
                categorized_skills[category][subcategory] = []

            categorized_skills[category][subcategory].append(skill)

        # Sort categories and subcategories
        sorted_categories = {}
        for category in sorted(categorized_skills.keys()):
            sorted_categories[category] = {}
            for subcategory in sorted(categorized_skills[category].keys()):
                # Sort skills within subcategory by short_description
                sorted_skills = sorted(
                    categorized_skills[category][subcategory],
                    key=lambda x: x.get('short_description', '')
                )
                sorted_categories[category][subcategory] = sorted_skills

        return render_template('skills_index.html', skills=sorted_categories)

    except Exception as e:
        import traceback
        print(f"DEBUG: Exception in skills route: {str(e)}")
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        return f"Error: {str(e)}", 500


@app.route('/api/skills', methods=['POST'])
@login_required
def update_skills():
    """
    API endpoint for updating skills via AJAX.
    """
    try:
        data = request.get_json()
        if not data:
            return flask_jsonify({'success': False, 'message': 'No data received'})

        user_id = session.get('user_id')
        worker = Worker(user_id)
        success, message = worker.process_skills_form(data)

        return flask_jsonify({'success': success, 'message': message})

    except Exception as e:
        return flask_jsonify({'success': False, 'message': str(e)})

@app.route('/employment_iter')
@login_required
def employment_iter():
    employer_id = request.args.get('employer_id')
    # Default values for a new employer
    return render_template(
        'employment_iter.html',
        id=employer_id,
        name="",
        location="",
        state=True,
        positions=[]
    )


@app.route('/achievements', methods=['GET', 'POST'])
@login_required
def achievements():
    user_id = session.get('user_id')
    worker = Worker(user_id)

    if request.method == 'POST':
        form_data = request.form.to_dict()

        print(f"DEBUG: Received form data: {form_data}")

        # Check for delete operations for standalone achievements
        if '_delete_achievement' in form_data:
            achievement_id = form_data['_delete_achievement']
            print(f"DEBUG: Deleting achievement with ID: {achievement_id}")
            result = worker.delete_entry("standalone_achievement", achievement_id)
            print(f"DEBUG: Deletion result: {result}")
            flash('Achievement deleted successfully', 'success')
            return redirect(url_for('achievements'))

        # Process new standalone achievements
        new_added = False
        for key in form_data:
            if key.startswith('new-achievement-') and key.endswith('_title'):
                achievement_id = key.split('_')[0]
                print(f"DEBUG: Processing new achievement with ID: {achievement_id}")

                title = form_data.get(f"{achievement_id}_title", "").strip()
                description = form_data.get(f"{achievement_id}_description", "").strip()
                date = form_data.get(f"{achievement_id}_date", "").strip()
                url = form_data.get(f"{achievement_id}_url", "").strip()
                enabled = 1 if f"{achievement_id}_enabled" in form_data else 0

                try:
                    achievement_order = int(form_data.get(f"{achievement_id}_achievement_order", 99))
                except:
                    achievement_order = 99

                print(f"DEBUG: New achievement data: title='{title}', desc='{description[:20]}...', enabled={enabled}")

                if title:  # Only add if title is not empty
                    print(f"DEBUG: Adding new achievement to database")
                    result = worker.add_standalone_achievement(
                        title=title,
                        description=description,
                        date=date,
                        url=url,
                        achievement_order=achievement_order
                    )
                    if result:
                        new_added = True
                        print(f"DEBUG: Successfully added achievement with ID: {result}")
                    else:
                        print(f"DEBUG: Failed to add achievement")

        # Process existing standalone achievements
        updates_made = False
        standalone_achievements = worker.get_all_achievements()
        print(f"DEBUG: Found {len(standalone_achievements)} existing achievements to update")

        for achievement in standalone_achievements:
            achievement_id = achievement['SK']
            if f"{achievement_id}_title" in form_data:
                print(f"DEBUG: Processing existing achievement update with ID: {achievement_id}")

                title = form_data.get(f"{achievement_id}_title", "").strip()
                description = form_data.get(f"{achievement_id}_description", "").strip()
                date = form_data.get(f"{achievement_id}_date", "").strip()
                url = form_data.get(f"{achievement_id}_url", "").strip()
                enabled = 1 if f"{achievement_id}_enabled" in form_data else 0

                try:
                    achievement_order = int(form_data.get(f"{achievement_id}_achievement_order", 99))
                except:
                    achievement_order = 99

                current_title = achievement.get('title', '')
                current_desc = achievement.get('description', '')
                current_date = achievement.get('date', '')
                current_url = achievement.get('url', '')
                current_state = achievement.get('state', 0)
                current_order = int(achievement.get('achievement_order', 99))

                print(f"DEBUG: Current data: title='{current_title}', enabled={current_state}")
                print(f"DEBUG: New data: title='{title}', enabled={enabled}")

                # Update only if something changed
                if (title != current_title or
                        description != current_desc or
                        date != current_date or
                        url != current_url or
                        enabled != current_state or
                        achievement_order != current_order):

                    print(f"DEBUG: Updating achievement in database")
                    result = worker.update_achievement(
                        achievement_id,
                        title=title,
                        description=description,
                        date=date,
                        url=url,
                        state=enabled,
                        achievement_order=achievement_order
                    )
                    if result:
                        updates_made = True
                        print(f"DEBUG: Successfully updated achievement")
                    else:
                        print(f"DEBUG: Failed to update achievement")

        if new_added or updates_made:
            flash('Achievements updated successfully', 'success')
        return redirect(url_for('achievements'))

    # GET request - display achievements
    achievements_data = worker.get_combined_achievements()
    print(f"DEBUG: Loading achievements page with {len(achievements_data)} achievements")

    # Count achievements by type
    standalone_count = sum(1 for a in achievements_data if a.get('achievement_type') == 'standalone')
    position_count = sum(1 for a in achievements_data if a.get('achievement_type') == 'position')
    print(f"DEBUG: Found {standalone_count} standalone and {position_count} position-related achievements")

    return render_template('achievements_index.html', payload=achievements_data, debug=True)

@app.route("/glossary")
@login_required
def glossary():
    # Initialize worker

    user_id = session.get('user_id')
    worker = Worker(user_id)

    # Get all glossary terms
    print("DEBUG: Retrieving glossary terms")
    terms = worker.get_glossary()
    print(f"DEBUG: Retrieved {len(terms)} glossary terms")

    # Transform the terms for display if needed
    # (Sort alphabetically by term)
    sorted_terms = sorted(terms, key=lambda x: x.get('term', '').lower())

    # Pass the terms to the glossary_index template
    return render_template("glossary_index.html", payload=sorted_terms)


@app.route("/glossary", methods=["POST"])
@login_required
def glossary_post():
    # Initialize worker
    from pylaform.database.templateWorker import Worker
    user_id = session.get('user_id')
    worker = Worker(user_id)

    # Process form data
    form_data = request.form.to_dict()

    # Handle deletions first
    if "_delete" in form_data:
        delete_id = form_data.get("_delete")
        if delete_id:
            if delete_id.startswith("new"):
                # This is a new item that was deleted before saving
                # Nothing to do in the database
                pass
            else:
                # Delete existing item
                worker.delete_entry("glossary", delete_id)
                flash("Glossary term deleted successfully", "success")

        # Redirect to avoid form resubmission
        return redirect(url_for("glossary"))

    # Process updates and new additions
    # Group form data by ID
    term_data = {}
    for key, value in form_data.items():
        if "_" in key:
            id_part, field_part = key.split("_", 1)
            if id_part not in term_data:
                term_data[id_part] = {}
            term_data[id_part][field_part] = value

    # Update existing items and add new ones
    for term_id, data in term_data.items():
        if term_id.startswith("new"):
            # Add new term
            if "term" in data and "definition" in data:
                worker.add_glossary(
                    term=data["term"],
                    definition=data["definition"]
                )
        else:
            # Update existing term
            worker.update_glossary(term_id, **data)

    flash("Glossary terms updated successfully", "success")
    return redirect(url_for("glossary"))


@app.route("/linkedin-settings")
@login_required
def linkedin_settings():
    return render_template("linkedin_settings.html")


@app.route("/linkedin-import")
@login_required
def linkedin_import_page():
    """
    Page for importing LinkedIn data
    """
    return render_template("linkedin_import.html")


# Add API routes for AI helper
@app.route("/api/ai-status")
@login_required
def ai_status():
    # Simplified status check for now
    return {"status": "ok", "message": "Amazon Q is available"}


@app.route("/api/improve-text", methods=["POST"])
@login_required
def improve_text():
    # Placeholder for text improvement API
    try:
        data = request.get_json()
        text = data.get("text", "")
        improvement_type = data.get("type", "")

        # For now, return the same text as a placeholder
        return {"response": f"Improved text would appear here. Type: {improvement_type}"}
    except Exception as e:
        return {"error": str(e)}


@app.route("/ai-config")
@login_required
def ai_config():
    return render_template("ai_config.html")


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        table = db()

        # Find user by email
        response = table.query(
            IndexName='EmailIndex',
            KeyConditionExpression='email = :email',
            ExpressionAttributeValues={':email': email}
        )

        if not response['Items']:
            flash("Invalid email or password", "error")
            return render_template('login.html')

        user = response['Items'][0]

        if not verify_password(user['password'], password):
            flash("Invalid email or password", "error")
            return render_template('login.html')

        # Create session
        session_id = create_session(table, user['PK'].split('#')[1])

        # Store in Flask session
        session['user_id'] = user['PK'].split('#')[1]
        session['session_id'] = session_id
        session['user_name'] = user.get('name', '')

        next_url = request.args.get('next')
        return redirect(next_url if next_url else url_for('landing'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Handle user registration.
    """
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')

        logger.info(f"Registration attempt: {email}")

        # Validate password
        is_valid, message = validate_password(password)
        logger.info(f"Password validation result: {is_valid}, message: {message}")
        if not is_valid:
            flash(message, "error")
            logger.error(f"Password validation failed: {message}")
            return render_template('register.html',
                                   email=email,
                                   first_name=first_name,
                                   last_name=last_name)

        try:
            table = db()
            result = create_user(table, email, password, first_name, last_name)
            logger.info(f"create_user result: {result}")
            if not result:
                flash("Email already registered", "error")
                logger.error("Email already registered")
                return render_template('register.html',
                                       email=email,
                                       first_name=first_name,
                                       last_name=last_name)

            # Create default identification records for the new user
            create_user_identification(table, result)
            logger.info(f"Created default identification records for user {result}")
        except Exception as e:
            flash(f"Error creating user: {str(e)}", "error")
            logger.exception("Exception during user creation")
            return render_template('register.html',
                                   email=email,
                                   first_name=first_name,
                                   last_name=last_name)

        try:
            session_id = create_session(table, result)
            logger.info(f"create_session result: {session_id}")
            if session_id:
                session['user_id'] = result
                session['session_id'] = session_id
                flash("Registration successful!", "success")
                return redirect(url_for('index'))
            else:
                flash("Registration failed (session)", "error")
                logger.error("Session creation failed")
                return render_template('register.html')
        except Exception as e:
            flash(f"Error creating session: {str(e)}", "error")
            logger.exception("Exception during session creation")
            return render_template('register.html')

    return render_template('register.html')

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """
    Handle password reset requests.
    GET: Display the forgot password form
    POST: Process the form and send reset email
    """
    if request.method == 'POST':
        email = request.form.get('email')

        if not email:
            flash("Please enter your email address", "warning")
            return render_template('forgot_password.html')

        try:
            table = db()
            # Check if user exists
            user = get_user_by_email(table, email)

            if not user:
                # Don't reveal if email exists or not for security
                flash("If your email is registered, you will receive a password reset link shortly.", "info")
                return render_template('reset_email_sent.html')

            # Generate a secure token
            token = secrets.token_urlsafe(32)
            expiration = int(time.time()) + 86400  # 24 hours from now

            # Store the token in the database
            store_reset_token(table, user['PK'], token, expiration)

            # Send the reset email
            reset_url = url_for('reset_password', token=token, _external=True)
            send_password_reset_email(email, reset_url)

            logger.info(f"Password reset requested for {email}")
            return render_template('reset_email_sent.html')

        except Exception as e:
            logger.exception(f"Error in forgot_password: {str(e)}")
            flash("An error occurred. Please try again later.", "danger")

    return render_template('forgot_password.html')


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """
    Handle password reset with token.
    GET: Display the password reset form if token is valid
    POST: Process the form and update the password
    """
    if not token:
        flash("Invalid reset link", "danger")
        return render_template('reset_token_invalid.html')

    try:
        table = db()
        # Verify token and get user
        token_data = verify_reset_token(table, token)

        if not token_data:
            flash("The password reset link is invalid or has expired", "danger")
            return render_template('reset_token_invalid.html')

        user_id = token_data['user_id']

        if request.method == 'POST':
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')

            # Validate password
            if password != confirm_password:
                flash("Passwords do not match", "danger")
                return render_template('reset_password.html', token=token)

            is_valid, message = validate_password(password)
            if not is_valid:
                flash(message, "danger")
                return render_template('reset_password.html', token=token)

            # Update the password
            update_user_password(table, user_id, password)

            # Invalidate the token
            invalidate_reset_token(table, token)

            # Invalidate all sessions (optional)
            invalidate_all_sessions(table, user_id)

            logger.info(f"Password reset successful for user {user_id}")
            flash("Your password has been successfully reset", "success")
            return render_template('reset_success.html')

    except Exception as e:
        logger.exception(f"Error in reset_password: {str(e)}")
        flash("An error occurred. Please try again later.", "danger")
        return render_template('reset_password.html', token=token)

    return render_template('reset_password.html', token=token)


@app.route('/logout')
def logout():
    """
    Log out the current user by clearing their session data.

    :return: Redirect to the login page
    """
    # Clear session data
    session.clear()
    flash("You have been logged out successfully", "success")
    return redirect(url_for('login'))

app.register_blueprint(resume_bp, url_prefix='/resume')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)