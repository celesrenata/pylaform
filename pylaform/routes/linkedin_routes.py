import os
import logging
from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from pylaform.services.proxycurl_service import ProxycurlService
from pylaform.services.import_service import ImportService
from pylaform.commands.db import update, query, delete

# Create blueprint
linkedin_bp = Blueprint('linkedin', __name__,
                       url_prefix='/linkedin',
                       template_folder='../templates')

logger = logging.getLogger(__name__)


@linkedin_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    """LinkedIn settings configuration page"""
    from pylaform.services.config_service import ConfigService
    config_service = ConfigService()

    if request.method == 'POST':
        # Update LinkedIn settings from form
        proxycurl_api_key = request.form.get('proxycurl_api_key', '')

        # Save the API key to configuration
        config = config_service._load_config()  # Use _load_config instead of load_config
        config['linkedin'] = config.get('linkedin', {})
        config['linkedin']['proxycurl_api_key'] = proxycurl_api_key
        config_service._save_config(config)  # Use _save_config instead of save_config

        # Also set in environment for current session
        os.environ['PROXYCURL_API_KEY'] = proxycurl_api_key

        logger.info("Proxycurl API key updated")  # Use logger instead of app.logger
        flash("LinkedIn settings updated successfully", "success")
        return redirect(url_for('linkedin.settings'))

    # Get current settings
    config = config_service._load_config()  # Use _load_config instead of load_config
    linkedin_config = config.get('linkedin', {})
    proxycurl_api_key = linkedin_config.get('proxycurl_api_key', '')

    # Mask the API key if it's set
    masked_proxycurl_key = "••••••••••••" if proxycurl_api_key else ""

    # Also load into environment variables
    if proxycurl_api_key:
        os.environ['PROXYCURL_API_KEY'] = proxycurl_api_key

    # Check if the API key is set to determine if Proxycurl is available
    has_proxycurl = bool(proxycurl_api_key)

    return render_template('linkedin_settings.html',
                           proxycurl_api_key=masked_proxycurl_key,
                           has_proxycurl=has_proxycurl)


@linkedin_bp.route('/import-page')
def import_page():
    """LinkedIn import options page"""
    # Check if we have Proxycurl API key
    proxycurl_api_key = os.environ.get('PROXYCURL_API_KEY', '')

    return render_template('linkedin_import.html',
                           has_proxycurl=bool(proxycurl_api_key))


@linkedin_bp.route('/import-with-proxycurl', methods=['POST'])
def import_with_proxycurl():
    """Import LinkedIn data using Proxycurl API"""
    # Get LinkedIn profile URL from form
    linkedin_url = request.form.get('linkedin_profile_url', '')

    if not linkedin_url:
        flash("Please provide your LinkedIn profile URL", "warning")
        return redirect(url_for('linkedin.import_page'))

    # Validate URL format
    if not (linkedin_url.startswith('https://www.linkedin.com/') or
            linkedin_url.startswith('https://linkedin.com/')):
        flash("Please enter a valid LinkedIn profile URL", "warning")
        return redirect(url_for('linkedin.import_page'))

    # Initialize Proxycurl service
    proxycurl_service = ProxycurlService()

    # Fetch profile data
    profile_data = proxycurl_service.get_profile_data(linkedin_url)

    if 'error' in profile_data:
        flash(f"Error fetching LinkedIn data: {profile_data['error']}", "danger")
        return redirect(url_for('linkedin.import_page'))

    # Store profile data in session
    session['linkedin_profile_data'] = profile_data

    # Get selected sections to import
    import_sections = request.form.getlist('import_sections')

    # If no sections selected, select all by default
    if not import_sections:
        import_sections = ['basic_info', 'experience', 'education', 'skills']

    # Process the import
    try:
        import_service = ImportService()
        result = import_service.process_linkedin_import(profile_data, import_sections)

        if result['success']:
            sections_imported = ', '.join(result['imported_sections'])
            flash(f"Successfully imported LinkedIn data: {sections_imported}", "success")
        else:
            errors = ', '.join(result['errors'])
            flash(f"Errors during import: {errors}", "warning")

        # Clear the session data
        session.pop('linkedin_profile_data', None)

        return redirect(url_for('landing'))

    except Exception as e:
        logger.error(f"Error importing LinkedIn data: {str(e)}")
        flash(f"Error importing LinkedIn data: {str(e)}", "danger")
        return redirect(url_for('linkedin.import_page'))


@linkedin_bp.route('/import', methods=['POST'])
def import_data():
    """Process the LinkedIn data import - Legacy method"""
    # Check if we have profile data
    profile_data = session.get('linkedin_profile_data')

    if not profile_data:
        flash("LinkedIn data not available. Please reconnect your account.", "danger")
        return redirect(url_for('linkedin.import_page'))

    # Get selected sections to import
    import_sections = request.form.getlist('import_sections')

    if not import_sections:
        flash("Please select at least one section to import", "warning")
        return redirect(url_for('linkedin.import_page'))

    try:
        # Import basic information
        if 'basic_info' in import_sections:
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
                        logger.error(f"Error updating identification item {item['attr']}: {str(e)}")

        # Import work experience
        if 'experience' in import_sections and 'positions' in profile_data and profile_data['positions']:
            updater = update.Updates()
            deleter = delete.Deletes()

            try:
                # Get existing employment records
                employment_data = query.Queries().get_positions()

                # Delete existing records
                for item in employment_data:
                    deleter.single_row('positions', item['id'])
            except Exception as e:
                logger.error(f"Error clearing existing employment data: {str(e)}")

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
                    logger.error(f"Error adding position {idx}: {str(e)}")

        # Import education
        if 'education' in import_sections and 'education' in profile_data and profile_data['education']:
            updater = update.Updates()
            deleter = delete.Deletes()

            try:
                # Get existing education records
                education_data = query.Queries().get_education()

                # Delete existing records
                for item in education_data:
                    deleter.single_row('education', item['id'])
            except Exception as e:
                logger.error(f"Error clearing existing education data: {str(e)}")

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
                    logger.error(f"Error adding education {idx}: {str(e)}")

        # Import skills
        if 'skills' in import_sections and 'skills' in profile_data and profile_data['skills']:
            updater = update.Updates()
            deleter = delete.Deletes()

            try:
                # Get existing skills records
                skills_data = query.Queries().get_skills()

                # Delete existing records
                for item in skills_data:
                    deleter.single_row('skills', item['id'])
            except Exception as e:
                logger.error(f"Error clearing existing skills data: {str(e)}")

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
                    logger.error(f"Error adding skill {idx}: {str(e)}")

        flash("LinkedIn data successfully imported!", "success")

        # Clear the session data to avoid duplicate imports
        session.pop('linkedin_profile_data', None)

        # Redirect to the main resume page
        return redirect(url_for('landing'))

    except Exception as e:
        logger.error(f"Error importing LinkedIn data: {str(e)}")
        flash(f"Error importing LinkedIn data: {str(e)}", "danger")
        return redirect(url_for('linkedin.import_page'))