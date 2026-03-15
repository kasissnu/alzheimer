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

print("[STARTUP] All systems ready\n")

def seed_demo_memories(target_user_id: str):
	rag.add_memories([
		MemoryItem(user_id=target_user_id,
			text="Your daughter Ananya visited you last Sunday and brought roses.",
			relationship="daughter", event_type="family_visit", importance="high"),
		MemoryItem(user_id=target_user_id,
			text="Your son Rohan calls you every Friday evening.",
			relationship="son", event_type="phone_call", importance="high"),
		MemoryItem(user_id=target_user_id,
			text="Your doctor is Dr. Mehta at Apollo Hospital.",
			event_type="medical", importance="high"),
		MemoryItem(user_id=target_user_id,
			text="You love filter coffee every morning at 8am.",
			event_type="daily_routine", importance="medium"),
		MemoryItem(user_id=target_user_id,
			text="You were a school teacher for 30 years.",
			event_type="life_history", importance="high"),
	])

last_verified_user_id = None
last_verified_name = None

while True:
    print("\n[1] Register user")
    print("[2] Identify + ask question")
    print("[3] List users")
    print("[4] Seed demo memories")
    print("[5] Show conversation history")
    print("[6] Exit")

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
        last_verified_user_id = user_id
        last_verified_name = result.get('name') or user_id
        print(f"[STEP 2] Verified: {last_verified_name} [{user_id}] ({result['confidence']})")

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

        try:
            rag.store_conversation(
                user_id=user_id,
                question=question,
                answer=rag_result['response'],
                used_fallback=rag_result['used_fallback'],
                retrieved=rag_result.get('retrieved')
            )
        except Exception as e:
            print(f"[WARNING] Failed to store conversation: {e}")

    elif choice == "3":
        system.list_users()

    elif choice == "4":
        users = system.db.list_users()
        if not users:
            print("No users registered yet. Register and verify a user first.")
            continue

        target_user_id = last_verified_user_id
        if target_user_id:
            override = input(f"Seed memories for user_id (Enter for {target_user_id}): ").strip()
            if override:
                target_user_id = override
        else:
            print("\nSelect a user to seed demo memories:")
            for i, u in enumerate(users, 1):
                print(f"  [{i}] {u.get('name')} [{u.get('user_id', '?')}]")
            sel = input("Enter user number or user_id: ").strip()
            if sel.isdigit() and 1 <= int(sel) <= len(users):
                target_user_id = users[int(sel) - 1].get('user_id')
            else:
                target_user_id = sel

        if not target_user_id:
            print("Invalid user_id.")
            continue

        seed_demo_memories(target_user_id)
        print(f"[INFO] Seeded demo memories for {target_user_id}")

    elif choice == "5":
        target_user_id = last_verified_user_id
        if not target_user_id:
            target_user_id = input("Enter user_id to view history: ").strip()
        if not target_user_id:
            print("Invalid user_id.")
            continue

        history = rag.get_conversation_history(target_user_id, limit=10)
        if not history:
            print("No conversation history found.")
            continue

        print(f"\n=== Conversation History (last {len(history)}) ===")
        for item in history:
            ts = item.get("timestamp", "?")
            q = item.get("question", "")
            a = item.get("answer", "")
            print(f"[{ts}] Q: {q}")
            print(f"         A: {a}")

    elif choice == "6":
        system.cleanup()
        break

