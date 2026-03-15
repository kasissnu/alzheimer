
import whisper
from memory_rag import MemoryRAG
from biometric_system import BiometricMemorySystem

print("Loading Whisper...")
stt_model = whisper.load_model("base")

biometric_system = BiometricMemorySystem()
rag = MemoryRAG()

def run_pipeline(face_image, voice_audio, patient_audio):

    user_id = biometric_system.identify_person(face_image, voice_audio)

    if user_id is None:
        return "Speaker not recognized"

    transcript = stt_model.transcribe(patient_audio)["text"]

    response = rag.answer_query(user_id, transcript)

    return response
