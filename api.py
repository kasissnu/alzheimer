import os
import sys
import ssl
import time
import json
import base64
import numpy as np
import cv2
import whisper
import asyncio
from typing import Dict, List, Optional
from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# FIX: macOS Python SSL diffs
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

from biometric_memory_system import BiometricMemorySystem, SystemConfig, Logger
from conversation_store import ConversationStore
from conversation_summarizer import ConversationSummarizer
from memory_rag import MemoryRAG, RAGConfig

print("[STARTUP] Loading Fast API Backend...")

print("[STARTUP] Loading Whisper STT...")
stt_model = whisper.load_model("base")

print("[STARTUP] Loading Biometric System...")
config = SystemConfig()
system = BiometricMemorySystem(config)
conversation_store = ConversationStore()
summarizer = ConversationSummarizer()

print("[STARTUP] Loading RAG System...")
rag = MemoryRAG(RAGConfig())

app = FastAPI(title="MEMORA API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def transcribe_audio_bytes(audio_bytes: bytes) -> str:
    if not audio_bytes:
        return ""
    audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    result = stt_model.transcribe(audio_array, language="en")
    return result["text"].strip()


@app.get("/api/users")
def get_users():
    return system.db.list_users()

@app.delete("/api/users/{user_id}")
def delete_user(user_id: str):
    biometric_deleted = system.delete_user(user_id)
    history_deleted = conversation_store.delete_history(user_id)
    try:
        rag_count = rag.delete_memories_for_user(user_id)
    except:
        rag_count = 0
    
    return {
        "success": True,
        "user_id": user_id,
        "biometric_deleted": biometric_deleted,
        "history_deleted": history_deleted,
        "rag_deleted": rag_count
    }

@app.get("/api/history/{user_id}")
def get_history(user_id: str):
    history = conversation_store.get_history(user_id, limit=50)
    summary = summarizer.summarize(history) if history else "No context."
    return {"history": history, "summary": summary}


@app.post("/api/auth/identify")
async def identify(file: UploadFile = File(...)):
    image_data = await file.read()
    image_array = np.frombuffer(image_data, np.uint8)
    frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    
    if frame is None:
        raise HTTPException(status_code=400, detail="Invalid image")
        
    system.face_processor.clear()
    system.face_processor.frame_count = config.SKIP_FRAMES - 1
    face_emb = system.face_processor.process_frame(frame)
    
    if face_emb is None:
        return {"verified": False, "error": "No face detected in the image"}
        
    face_results, _ = system.db.search_user(face_emb, None)
    if face_results is None:
        return {"verified": False, "error": "Search failed"}
        
    result = system._face_only_results(face_results)
    return result


@app.post("/api/users/register")
async def register(
    name: str = Form(...), 
    face_image: UploadFile = File(...), 
    audio_file: Optional[UploadFile] = File(None)
):
    # 1. Process Face
    image_data = await face_image.read()
    image_array = np.frombuffer(image_data, np.uint8)
    frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    
    system.face_processor.clear()
    system.face_processor.frame_count = config.SKIP_FRAMES - 1
    face_emb = system.face_processor.process_frame(frame)
    if face_emb is None:
        raise HTTPException(status_code=400, detail="No face detected in the provided image")
    
    # 2. Process Voice
    voice_emb = None
    transcript = ""
    if audio_file:
        audio_data = await audio_file.read()
        if len(audio_data) > 0:
            system.voice_processor.clear()
            system.voice_processor.add_audio_chunk(audio_data)
            voice_emb = system.voice_processor.process_audio()
            # Also transcribe to save as first memory!
            transcript = transcribe_audio_bytes(audio_data)

    # If the system strictly requires a voice embedding based on FUSION_WEIGHT, we might error if None.
    # Currently _fuse_results falls back to mostly face if voice is missing, or we can just zero it out,
    # but the DB handles missing voice_emb by skipping voice collection addition.
    if voice_emb is None and config.FUSION_WEIGHT < 1.0:
        Logger.warning("No voice added for this user.")
        
    # Generate ID and Metadata manually
    user_id = f"{name.replace(' ', '_').lower()}_{int(time.time())}"
    metadata = {
        'user_id': user_id,
        'name': name,
        'registered_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'device': 'web'
    }
    
    success = system.db.add_user(user_id, face_emb, voice_emb, metadata)
    if not success:
        raise HTTPException(status_code=500, detail="Database insertion failed")
        
    if transcript:
        conversation_store.store_utterance(user_id, transcript, source="register")
        
    return {
        "success": True,
        "user_id": user_id,
        "name": name,
        "transcript_saved": transcript
    }


# WebSocket for real-time STT -> RAG -> Text streaming
@app.websocket("/api/chat/{user_id}")
async def chat_websocket(websocket: WebSocket, user_id: str):
    """
    Client sends binary audio chunks.
    When client sends text '__END_AUDIO__', we process the buffer, 
    run Whisper, run RAG, and stream JSON responses back.
    """
    await websocket.accept()
    audio_buffer = []

    try:
        while True:
            data = await websocket.receive()
            if "bytes" in data:
                audio_buffer.append(data["bytes"])
            elif "text" in data and data["text"] == "__END_AUDIO__":
                if not audio_buffer:
                    await websocket.send_json({"type": "error", "message": "No audio received"})
                    continue

                full_audio = b"".join(audio_buffer)
                audio_buffer.clear()
                
                # Transcribe
                await websocket.send_json({"type": "status", "message": "Transcribing..."})
                question = transcribe_audio_bytes(full_audio)
                await websocket.send_json({"type": "transcript", "text": question})
                
                if not question:
                    await websocket.send_json({"type": "error", "message": "Could not understand audio"})
                    continue
                
                # Fetch rag Context
                await websocket.send_json({"type": "status", "message": "Retrieving memories..."})
                rag_result = rag.generate_response(question, user_id=user_id)
                
                # Streaming out the response text
                text_response = rag_result["response"]
                await websocket.send_json({"type": "status", "message": "Generating response..."})
                
                # Simulate streaming words for UI effect (since original RAG is not async streaming right now)
                words = text_response.split(" ")
                for i, word in enumerate(words):
                    await websocket.send_json({
                        "type": "stream", 
                        "chunk": word + " " if i < len(words) - 1 else word,
                        "done": i == len(words) - 1
                    })
                    await asyncio.sleep(0.02)
                
                # Store
                conversation_store.store_utterance(user_id, question, source="chat_q")
                conversation_store.store_utterance(user_id, text_response, source="chat_a")
                try:
                    rag.store_conversation(
                        user_id=user_id,
                        question=question,
                        answer=text_response,
                        used_fallback=rag_result["used_fallback"],
                        retrieved=rag_result.get("retrieved")
                    )
                except Exception as e:
                    Logger.warning(f"Failed to store RAG context: {e}")
                    
                await websocket.send_json({"type": "complete"})

    except WebSocketDisconnect:
        print(f"Client {user_id} disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
