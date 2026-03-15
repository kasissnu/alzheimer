
from flask import Flask, request, jsonify, render_template
from main import run_pipeline

app = Flask(__name__)

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/identify", methods=["POST"])
def identify():
    face = request.files.get("face")
    voice = request.files.get("voice")
    speech = request.files.get("speech")

    face_path = "temp_face.jpg"
    voice_path = "temp_voice.wav"
    speech_path = "temp_patient.wav"

    face.save(face_path)
    voice.save(voice_path)
    speech.save(speech_path)

    response = run_pipeline(face_path, voice_path, speech_path)

    return jsonify({"response": response})

if __name__ == "__main__":
    app.run(debug=True)
