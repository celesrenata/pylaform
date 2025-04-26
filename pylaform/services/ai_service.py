# pylaform/services/ai_service.py
import requests
import json


class OllamaService:
    """Service to interact with Ollama API for resume improvements"""

    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
        self.model = "llama3.2:1b"

    def generate_improvement(self, text, improvement_type):
        """
        Generate an improvement for the given text based on the specified type

        :param text: Text to improve
        :param improvement_type: Type of improvement (tenet, list, sentence_restructure, sentence_summarization)
        :return: Improved text from the AI
        """
        # Detailed instructions for each improvement type
        system_instructions = {
            "tenet": """You are an expert resume coach helping users improve their resume statements.
                When given a statement, transform it into a clear, concise principle or tenet that demonstrates 
                professional values and work ethic. Use active voice, professional language, and focus on 
                qualities employers value. For example, turn "I always try to get my work done on time" into 
                "Committed to meeting deadlines through proactive time management and prioritization skills."
                Only return the improved statement without any explanations.""",

            "list": """You are an expert resume coach helping users improve their resume content.
                Transform the given paragraph or text into a well-formatted, concise list suitable for a resume.
                Extract the key points, use action verbs at the beginning of each bullet point, quantify achievements
                where possible, and ensure each point is concise yet impactful. Format as bullet points with a dash (-)
                at the beginning of each point. Only return the improved list without any explanations.""",

            "sentence_restructure": """You are an expert resume coach helping users improve their resume sentences.
                Rewrite the given sentence to be more impactful and clear for a resume. Use active voice, powerful action verbs,
                quantify achievements where possible, and highlight skills or results. For example, turn
                "I was responsible for managing a team" into "Led a cross-functional team of 8 members, increasing
                productivity by 27% through streamlined processes." Only return the improved sentence without explanations.""",

            "sentence_summarization": """You are an expert resume coach helping users improve their resume content.
                Summarize the given text into a concise, powerful statement for a resume, highlighting key achievements,
                skills, and results. Eliminate unnecessary details, focus on impact, use active voice, and incorporate
                industry-relevant keywords. Keep the summary under 25 words while maximizing impact.
                Only return the improved summary without explanations."""
        }

        if improvement_type not in system_instructions:
            return {"error": "Invalid improvement type"}

        try:
            # Format the JSON payload
            payload = {
                "model": self.model,
                "prompt": f"{system_instructions[improvement_type]}\n\nText to improve: {text}",
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 300
                }
            }

            # Make sure our payload is valid JSON
            headers = {
                "Content-Type": "application/json"
            }

            # Send the request
            response = requests.post(
                f"{self.base_url}/api/generate",
                headers=headers,
                data=json.dumps(payload)
            )

            # Check for successful response
            if response.status_code == 200:
                try:
                    result = response.json()
                    return {"response": result.get("response", "")}
                except json.JSONDecodeError as e:
                    # Handle case where response isn't valid JSON
                    return {"error": f"Invalid JSON response: {str(e)}", "raw_response": response.text}
            else:
                return {"error": f"API Error: {response.status_code}", "details": response.text}

        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}