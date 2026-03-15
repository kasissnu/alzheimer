class BiometricMemorySystem:

    def __init__(self):

        # Example known identities
        self.known_faces = {
            "face.jpg": "rahul_singh"
        }

        self.known_voices = {
            "speaker_voice.wav": "rahul_singh"
        }

    # ----------------------------------
    # Main identity function
    # ----------------------------------

    def identify_person(self, face_image, voice_audio):

        face_id = self.recognize_face(face_image)
        voice_id = self.recognize_voice(voice_audio)

        print("Face detected:", face_id)
        print("Voice detected:", voice_id)

        # Identity fusion
        if face_id == voice_id:
            return face_id

        return None

    # ----------------------------------

    def recognize_face(self, image):

        return self.known_faces.get(image)

    # ----------------------------------

    def recognize_voice(self, audio):

        return self.known_voices.get(audio)
