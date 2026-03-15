
import whisper
from memory_rag import MemoryRAG
from biometric_system import BiometricMemorySystem
from TTS.api import TTS

print("Loading Whisper...")
stt_model = whisper.load_model("base")

print("Loading TTS...")
tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")

biometric_system = BiometricMemorySystem()
rag = MemoryRAG()

def run_pipeline(face_image, voice_audio, patient_audio):

    user_id = biometric_system.identify_person(face_image, voice_audio)

    if user_id is None:
        return "Speaker not recognized"

    transcript = stt_model.transcribe(patient_audio)["text"]

    response = rag.answer_query(user_id, transcript)

    tts.tts_to_file(text=response, file_path="response.wav")

    return response
