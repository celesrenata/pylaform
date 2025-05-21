@app.route('/ai-config', methods=['GET', 'POST'])
def ai_config():
    if request.method == 'POST':
        # Update Amazon Q configuration
        app_id = request.form.get('amazon_q_app_id')
        region = request.form.get('aws_region')

        # Save to configuration or database
        # ...

        # Test connection with the new settings
        q_service = get_q_service(region=region, application_id=app_id)
        success, message = q_service.check_connection()

        if success:
            flash('Amazon Q connection successful!', 'success')
        else:
            flash(f'Amazon Q connection failed: {message}', 'error')

        return redirect(url_for('ai_config'))

    # GET request - show the form
    current_config = {
        'app_id': os.environ.get('AMAZON_Q_APP_ID', ''),
        'region': os.environ.get('AWS_REGION', 'us-east-1')
    }

    return render_template('ai_config.html', config=current_config)
