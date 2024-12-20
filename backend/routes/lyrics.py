import os
from flask import Blueprint, request, jsonify, send_file
from openai import OpenAI
from firebase import db  # Import Firestore client
from firebase_admin import firestore  # For Firestore timestamp
from dotenv import load_dotenv
from io import BytesIO
from fpdf import FPDF

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")  # Ensure your API key is set
)

# Create a Flask blueprint
lyrics_bp = Blueprint("lyrics", __name__)

@lyrics_bp.route("/", methods=["POST"])
def generate_lyrics():
    """
    Generate lyrics using OpenAI's latest client interface with validation.
    Save generated lyrics to Firestore.
    """
    data = request.json

    # Extract inputs and set defaults
    theme = data.get("theme", "life")
    mood = data.get("mood", "neutral")
    genre = data.get("genre", "general")
    max_tokens = data.get("max_tokens", 200)
    temperature = data.get("temperature", 0.7)
    rhyme_scheme = data.get("rhyme_scheme")

    # Validate inputs
    if not isinstance(max_tokens, int) or not (1 <= max_tokens <= 2048):
        return jsonify({"error": "max_tokens must be an integer between 1 and 2048"}), 400
    if not isinstance(temperature, (int, float)) or not (0 <= temperature <= 1):
        return jsonify({"error": "temperature must be a float between 0 and 1"}), 400
    if rhyme_scheme and not isinstance(rhyme_scheme, str):
        return jsonify({"error": "rhyme_scheme must be a string"}), 400

    # Construct the prompt
    prompt = f"Write a {mood} {genre} song about {theme}."
    if rhyme_scheme:
        prompt += f" The song should follow a {rhyme_scheme} rhyme scheme."

    try:
        # Call OpenAI API to generate chat completion
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="gpt-4",
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # Extract the generated lyrics
        lyrics = response.choices[0].message.content.strip()

        # Save lyrics to Firestore
        db.collection("lyrics").add({
            "theme": theme,
            "mood": mood,
            "genre": genre,
            "lyrics": lyrics,
            "created_at": firestore.SERVER_TIMESTAMP
        })

        return jsonify({
            "theme": theme,
            "mood": mood,
            "genre": genre,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "rhyme_scheme": rhyme_scheme,
            "lyrics": lyrics
        }), 200

    except Exception as e:
        # Handle exceptions and return error response
        return jsonify({"error": str(e)}), 500


@lyrics_bp.route("/export-txt/", methods=["POST"])
def export_txt():
    """
    Export lyrics as a text file.
    """
    data = request.json
    lyrics = data.get("lyrics")
    if not lyrics:
        return jsonify({"error": "Lyrics are required to export"}), 400

    try:
        # Create a text file in memory
        text_file = BytesIO()
        text_file.write(lyrics.encode("utf-8"))
        text_file.seek(0)

        return send_file(
            text_file,
            as_attachment=True,
            download_name="lyrics.txt",
            mimetype="text/plain"
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@lyrics_bp.route("/export-pdf/", methods=["POST"])
def export_pdf():
    """
    Export lyrics as a PDF file.
    """
    data = request.json
    lyrics = data.get("lyrics")
    if not lyrics:
        return jsonify({"error": "Lyrics are required to export"}), 400

    try:
        # Create a PDF file in memory
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, lyrics)

        pdf_file = BytesIO()
        pdf.output(pdf_file)
        pdf_file.seek(0)

        return send_file(
            pdf_file,
            as_attachment=True,
            download_name="lyrics.pdf",
            mimetype="application/pdf"
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
