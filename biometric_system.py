
class BiometricMemorySystem:

    def __init__(self):
        self.known_faces={"temp_face.jpg":"rahul_singh"}
        self.known_voices={"temp_voice.wav":"rahul_singh"}

    def identify_person(self, face_image, voice_audio):

        face_id=self.recognize_face(face_image)
        voice_id=self.recognize_voice(voice_audio)

        if face_id==voice_id:
            return face_id

        return None

    def recognize_face(self,image):
        return self.known_faces.get(image)

    def recognize_voice(self,audio):
        return self.known_voices.get(audio)
