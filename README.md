# Memora Cognitive Assistive System

This project helps Alzheimer’s patients recognize people around them.

Pipeline:

Camera + Microphone
↓
ArcFace Face Recognition
+
ECAPA-TDNN Speaker Recognition
↓
Identity Fusion
↓
user_id
↓
Whisper Speech Recognition
↓
Memory RAG Retrieval
↓
LLM Response
↓
Coqui TTS Speech Output
