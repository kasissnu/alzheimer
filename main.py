import json
import threading
import numpy as np
import whisper
from biometric_memory_system import BiometricMemorySystem, SystemConfig
from memory_rag import MemoryRAG, MemoryItem, RAGConfig

# rename your file to biometric_memory_system.py
# or change the import above to match your filename

print("[STARTUP] Loading Whisper STT...")
stt_model = whisper.load_model("base")

def transcribe(audio_buffer: list) -> str:
    audio_data = b''.join(audio_buffer)
    audio_array = (np.frombuffer(audio_data, dtype=np.int16)
                   .astype(np.float32) / 32768.0)
    result = stt_model.transcribe(audio_array, language="en")
    return result["text"].strip()

print("[STARTUP] Loading biometric system...")
config = SystemConfig()
system = BiometricMemorySystem(config)

print("[STARTUP] Loading RAG system...")
rag = MemoryRAG(RAGConfig())

print("[STARTUP] Loading demo memories...")
rag.add_memories([
    MemoryItem(user_id="qq",
        text="Your daughter Ananya visited you last Sunday and brought roses.",
        relationship="daughter", event_type="family_visit", importance="high"),
    MemoryItem(user_id="qq",
        text="Your son Rohan calls you every Friday evening.",
        relationship="son", event_type="phone_call", importance="high"),
    MemoryItem(user_id="qq",
        text="Your doctor is Dr. Mehta at Apollo Hospital.",
        event_type="medical", importance="high"),
    MemoryItem(user_id="qq",
        text="You love filter coffee every morning at 8am.",
        event_type="daily_routine", importance="medium"),
    MemoryItem(user_id="qq",
        text="You were a school teacher for 30 years.",
        event_type="life_history", importance="high"),
])
print("[STARTUP] All systems ready\n")

while True:
    print("\n[1] Register user")
    print("[2] Identify + ask question")
    print("[3] List users")
    print("[4] Exit")

    choice = input("\nEnter choice: ").strip()

    if choice == "1":
        name = input("Enter name: ").strip()
        if name:
            system.register_user(name)

    elif choice == "2":
        # Step 1 — identify who
        print("\n[STEP 1] Look at camera and speak (5 seconds)...")
        result = system.verify_user()

        if not result or not result['verified']:
            print("Could not verify identity. Try again.")
            continue

        user_id = result['identity']
        print(f"[STEP 2] Verified: {user_id} ({result['confidence']})")

        # Step 2 — listen for question
        print("\n[STEP 3] Ask your question now (7 seconds)...")
        system.voice_processor.clear()
        system.running = True
        aud_thread = threading.Thread(
            target=system._audio_worker, args=(7,)
        )
        aud_thread.start()
        aud_thread.join()
        system.running = False

        # Step 3 — transcribe
        question = transcribe(system.voice_processor.audio_buffer)
        print(f"[STEP 4] Heard: {question}")

        if not question:
            print("Could not hear question. Please try again.")
            continue

        # Step 4 — RAG answer
        rag_result = rag.generate_response(question, user_id=user_id)
        print(f"\n[MEMORA] {rag_result['response']}")

        if rag_result['used_fallback']:
            print("[INFO] No matching memory found")
        else:
            best = rag_result['retrieved'][0]
            print(f"[INFO] Memory similarity: {best['similarity']:.2f}")

    elif choice == "3":
        system.list_users()

    elif choice == "4":
        system.cleanup()
        break


