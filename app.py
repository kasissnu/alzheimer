
from flask import Flask, request, jsonify, send_file
from main import run_pipeline

app = Flask(__name__)

@app.route("/")
def dashboard():
    return open("dashboard.html").read()

@app.route("/add-memory")
def add_memory():
    return open("add_memory.html").read()

@app.route("/person")
def person():
    return open("person_info.html").read()

@app.route("/voice")
def voice():
    return open("voice_assistant.html").read()

@app.route("/search")
def search():
    return open("memory_search.html").read()

@app.route("/identify", methods=["POST"])
def identify():

    face=request.files.get("face")
    voice=request.files.get("voice")
    speech=request.files.get("speech")

    face_path="temp_face.jpg"
    voice_path="temp_voice.wav"
    speech_path="temp_patient.wav"

    face.save(face_path)
    voice.save(voice_path)
    speech.save(speech_path)

    response=run_pipeline(face_path,voice_path,speech_path)

    return jsonify({"response":response})

if __name__=="__main__":
    app.run(debug=True)
