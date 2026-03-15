import whisper
from memory_rag import MemoryRAG
from biometric_system import BiometricMemorySystem
from TTS.api import TTS

# -----------------------
# Load models once
# -----------------------

print("Loading Whisper...")
stt_model = whisper.load_model("base")

print("Loading TTS...")
tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")

print("Loading biometric system...")
biometric_system = BiometricMemorySystem()

print("Loading RAG...")
rag = MemoryRAG()

print("System ready\n")


def run_pipeline(face_image, voice_audio, patient_audio):

    # 1️⃣ Identify the speaker
    user_id = biometric_system.identify_person(face_image, voice_audio)

    if user_id is None:
        response = "I'm not sure who is speaking."
        print(response)
        tts.tts_to_file(text=response, file_path="response.wav")
        return

    print("Speaker identified:", user_id)

    # 2️⃣ Transcribe patient speech
    transcript = stt_model.transcribe(patient_audio)["text"]
    print("Patient said:", transcript)

    # 3️⃣ Ask RAG
    response = rag.answer_query(user_id, transcript)

    print("Assistant:", response)

    # 4️⃣ Speak response
    tts.tts_to_file(text=response, file_path="response.wav")

    return response


if __name__ == "__main__":

    # Example demo inputs
    face_image = "face.jpg"
    voice_audio = "speaker_voice.wav"
    patient_audio = "patient_question.wav"

    run_pipeline(face_image, voice_audio, patient_audio)
