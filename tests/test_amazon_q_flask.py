from flask import Flask, request, jsonify
import os
import logging
import boto3
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Import the AmazonQService
from pylaform.services.amazon_q_service import AmazonQService

# Create Flask app
app = Flask(__name__)


@app.route('/api/amazon-q-status')
def check_amazon_q_status():
    """Check if Amazon Q is available and configured"""
    service = AmazonQService(
        region=os.environ.get('AWS_REGION'),
        application_id=os.environ.get('AMAZON_Q_APP_ID')
    )

    success, message = service.check_connection()

    if success:
        return jsonify({
            'status': 'ok',
            'message': message
        })
    else:
        return jsonify({
            'status': 'error',
            'message': message
        })


@app.route('/api/amazon-q-improve', methods=['POST'])
def improve_with_amazon_q():
    """Improve text using Amazon Q"""
    try:
        data = request.json

        if not data or 'text' not in data or 'type' not in data:
            return jsonify({
                'error': 'Missing required fields: text and type'
            }), 400

        text = data['text']
        improvement_type = data['type']

        service = AmazonQService(
            region=os.environ.get('AWS_REGION'),
            application_id=os.environ.get('AMAZON_Q_APP_ID')
        )

        # Set improvement prompts
        service.improvement_prompts = {
            "tenet": "Transform the following text into a compelling resume core principle/tenet:",
            "list": "Convert the following paragraph into a bulleted list format suitable for a resume:",
            "sentence_restructure": "Restructure the following resume sentence to make it more impactful:",
            "sentence_summarization": "Summarize the following resume content into a concise statement:"
        }

        result = service.improve_text(text, improvement_type)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'error': f"Server error: {str(e)}"}), 500


@app.route('/')
def home():
    """Home page with simple instructions"""
    return """
    <html>
        <head>
            <title>Amazon Q Test</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }
                pre {
                    background-color: #f0f0f0;
                    padding: 10px;
                    border-radius: 4px;
                    overflow-x: auto;
                }
                .endpoint {
                    background-color: #e9f7fe;
                    padding: 15px;
                    border-left: 4px solid #0078d7;
                    margin-bottom: 20px;
                }
            </style>
        </head>
        <body>
            <h1>Amazon Q API Test Application</h1>

            <div class="endpoint">
                <h2>Check Status</h2>
                <p>GET /api/amazon-q-status</p>
                <a href="/api/amazon-q-status">Test it</a>
            </div>

            <div class="endpoint">
                <h2>Improve Text</h2>
                <p>POST /api/amazon-q-improve</p>
                <p>Body example:</p>
                <pre>
{
    "text": "I designed database schemas for the company's product.",
    "type": "tenet"
}
                </pre>
            </div>

            <h2>Test with curl:</h2>
            <pre>
curl -X POST http://localhost:5000/api/amazon-q-improve \\
  -H "Content-Type: application/json" \\
  -d '{"text": "I designed database schemas for the company product.", "type": "tenet"}'
            </pre>
        </body>
    </html>
    """


if __name__ == '__main__':
    # Get the port from environment or use 5000 as default
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)