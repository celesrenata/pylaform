# Pylaform - Modern Resume Generator

## Overview
Pylaform is a dynamic, web-based resume generator that combines Python, PyLaTeX, and modern web technologies to create professional-looking resumes. With an AI-powered resume improvement helper and a clean, responsive UI, Pylaform makes the resume creation process efficient and enjoyable.

## Features
- **Web-based UI**: Clean, Bootstrap-powered interface for easy resume editing
- **AI Resume Helper**: Integrated AI assistant to improve your resume content with:
  - Core principle/tenet highlighting
  - Text-to-list conversion
  - Sentence restructuring
  - Content summarization
- **PDF Generation**: High-quality PDF output using LaTeX templates
- **Multiple Sections**: Support for contact information, summary, education, certifications, skills, employment history, and achievements
- **Local AI Integration**: Optional Ollama integration for privacy-focused AI assistance

## Installation Instructions

### Standard Installation
1. Clone the repository:
```
git clone https://github.com/celesrenata/pylaform.git
cd pylaform
```


2. Set up a virtual environment (recommended):
```
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```


3. Install dependencies:
```
pip install -r requirements.txt
```


4. Install LaTeX class file:
   - Navigate to the `resources` directory
   - Follow one of these guides to install the `res.cls` class:
     * [Windows](https://tex.stackexchange.com/questions/2063/how-can-i-manually-install-a-package-on-miktex-windows)
     * [Mac and Linux](https://tex.stackexchange.com/questions/8357/how-to-have-local-package-override-default-package)

5. Run the application:
```
python app.py
```


6. Open your browser and go to `http://127.0.0.1:5000`

### Docker Installation

1. Clone the repository:
```
git clone https://github.com/celesrenata/pylaform.git
cd pylaform
```


2. Build and run using Docker Compose:
```
docker-compose up
```


3. Open your browser and go to `http://127.0.0.1:5000`

## AI Resume Helper Configuration

The AI resume helper is an optional feature that can improve your resume content.

### When running directly on your machine:

1. Install Ollama from [ollama.ai](https://ollama.ai/)
2. Start the Ollama service on your computer
3. In the Pylaform web interface:
   - Click the AI Resume Helper at the bottom of the screen
   - Click the settings gear icon
   - Enable AI Features toggle
   - Set Ollama Server URL to: `http://localhost:11434`
   - Choose a model (e.g., gemma3:1b)
   - Click "Save Settings"

### When using Docker:

1. No additional installation needed - Ollama is included in the docker-compose file
2. In the Pylaform web interface:
   - Click the AI Resume Helper at the bottom of the screen
   - Click the settings gear icon
   - Enable AI Features toggle
   - Set Ollama Server URL to: `http://ollama:11434`
   - Choose a model (e.g., gemma3:1b)
   - Click "Save Settings"

## Usage

1. Navigate through the sidebar to edit different sections of your resume
2. Use the AI Helper to improve text content by:
   - Selecting content type (Core Principle, List, Restructure, Summarize)
   - Entering your text
   - Clicking "Improve Text"
3. Click "Generate PDF" to create your polished resume

## Development

- Built with Python 3.12, Flask, PyLaTeX, and Bootstrap 5
- Uses modern JavaScript for the interactive components
- Integrates with Ollama for local AI processing

## Future Plans
- Additional LaTeX templates
- More AI improvement options
- Export to different formats
- Enhanced UI customization

## License
[MIT License](LICENSE)

## Contributors
Developed by Celes Hillyerd
GitHub: [@celesrenata](https://github.com/celesrenata)

---

Ready to create an impressive resume? Get started with Pylaform today!