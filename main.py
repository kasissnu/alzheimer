import threading
from typing import Dict, List, Optional

import numpy as np
import whisper

from biometric_memory_system import BiometricMemorySystem, SystemConfig
from memory_rag import MemoryRAG, RAGConfig


print("[STARTUP] Loading Whisper STT...")
stt_model = whisper.load_model("base")


def transcribe(audio_buffer: List[bytes]) -> str:
    audio_data = b"".join(audio_buffer)
    audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
    result = stt_model.transcribe(audio_array, language="en")
    return result["text"].strip()


print("[STARTUP] Loading biometric system...")
config = SystemConfig()
system = BiometricMemorySystem(config)

print("[STARTUP] Preparing RAG system...")
rag = MemoryRAG(RAGConfig())
print("[STARTUP] All systems ready\n")


def format_user_label(user: Dict) -> str:
    return f"{user.get('name', 'Unknown')} [{user.get('user_id', '?')}]"


def build_user_index(include_history_only: bool = False) -> List[Dict]:
    users = system.db.list_users()
    history_ids = set(rag.list_conversation_users())
    indexed_users: List[Dict] = []
    seen_user_ids = set()

    for user in users:
        user_id = user.get("user_id")
        if not user_id or user_id in seen_user_ids:
            continue
        has_history = user_id in history_ids
        if include_history_only and not has_history:
            continue

        user_copy = dict(user)
        user_copy["has_history"] = has_history
        indexed_users.append(user_copy)
        seen_user_ids.add(user_id)

    for user_id in sorted(history_ids):
        if user_id in seen_user_ids:
            continue
        indexed_users.append(
            {
                "user_id": user_id,
                "name": "Unknown",
                "registered_at": "history only",
                "has_history": True,
            }
        )

    return indexed_users


def prompt_for_user_id(prompt_text: str, *, history_only: bool = False) -> Optional[str]:
    users = build_user_index(include_history_only=history_only)
    if not users:
        if history_only:
            print("No conversation histories found.")
        else:
            print("No users found.")
        return None

    print()
    for index, user in enumerate(users, start=1):
        history_marker = " | history" if user.get("has_history") else ""
        registered_at = user.get("registered_at", "unknown")
        print(f"[{index}] {format_user_label(user)} ({registered_at}){history_marker}")

    selection = input(f"{prompt_text} ").strip()
    if not selection:
        return None

    if selection.isdigit():
        selection_index = int(selection)
        if 1 <= selection_index <= len(users):
            return users[selection_index - 1].get("user_id")

    return selection


def resolve_user_status(user_id: str) -> Dict[str, Optional[object]]:
    status = {
        "memory_count": None,
        "has_history": False,
        "memory_error": None,
    }

    try:
        status["memory_count"] = rag.get_user_memory_count(user_id)
    except Exception as exc:
        status["memory_error"] = str(exc)

    status["has_history"] = bool(rag.get_conversation_history(user_id, limit=1))
    return status


def ask_question_flow() -> None:
    print("\n[STEP 1] Look at camera and speak (5 seconds)...")
    result = system.verify_user()

    if not result or not result.get("verified"):
        print("This appears to be a new person or an unrecognized user.")
        return

    user_id = result["identity"]
    display_name = result.get("name") or user_id
    print(f"[STEP 2] Verified: {display_name} [{user_id}] ({result['confidence']})")

    print("\n[STEP 3] Ask your question now (7 seconds)...")
    system.voice_processor.clear()
    system.running = True
    audio_thread = threading.Thread(target=system._audio_worker, args=(7,))
    audio_thread.start()
    audio_thread.join()
    system.running = False

    question = transcribe(system.voice_processor.audio_buffer)
    print(f"[STEP 4] Heard: {question}")

    if not question:
        print("Could not hear question. Please try again.")
        return

    user_status = resolve_user_status(user_id)

    if user_status["memory_count"] == 0 and not user_status["has_history"]:
        rag_result = {
            "response": "I do not have any memories for you yet. You seem to be a new person in the system.",
            "retrieved": [],
            "used_fallback": True,
        }
    else:
        rag_result = rag.generate_response(question, user_id=user_id)
        if user_status["memory_error"]:
            print(f"[WARNING] Memory store check failed: {user_status['memory_error']}")
        if rag_result.get("error"):
            print(f"[WARNING] RAG unavailable, using safe fallback: {rag_result['error']}")

    print(f"\n[MEMORA] {rag_result['response']}")

    if rag_result["retrieved"]:
        best = rag_result["retrieved"][0]
        print(f"[INFO] Memory similarity: {best['similarity']:.2f}")
    elif user_status["memory_count"] == 0 and not user_status["has_history"]:
        print("[INFO] No memories or conversation history found for this user yet")
    else:
        print("[INFO] No matching memory found")

    try:
        rag.store_conversation(
            user_id=user_id,
            question=question,
            answer=rag_result["response"],
            used_fallback=rag_result["used_fallback"],
            retrieved=rag_result.get("retrieved"),
        )
    except Exception as exc:
        print(f"[WARNING] Failed to store conversation: {exc}")


def delete_user_flow() -> None:
    user_id = prompt_for_user_id("Enter user number or user_id to delete:")
    if not user_id:
        print("Invalid user selection.")
        return

    confirmation = input(f"Type DELETE to remove '{user_id}' from the system: ").strip()
    if confirmation != "DELETE":
        print("Delete cancelled.")
        return

    biometric_deleted = system.delete_user(user_id)

    try:
        memory_count = rag.delete_memories_for_user(user_id)
    except Exception as exc:
        memory_count = None
        print(f"[WARNING] Failed to delete memories for {user_id}: {exc}")

    history_deleted = rag.delete_conversation_history(user_id)

    if biometric_deleted:
        print(f"[INFO] Deleted biometric records for {user_id}")
    if memory_count is not None:
        print(f"[INFO] Deleted {memory_count} stored memories for {user_id}")
    if history_deleted:
        print(f"[INFO] Deleted conversation history for {user_id}")
    elif memory_count is not None:
        print(f"[INFO] No conversation history found for {user_id}")


def show_history_flow() -> None:
    user_id = prompt_for_user_id("Enter user number or user_id to inspect history:", history_only=True)
    if not user_id:
        print("Invalid user selection.")
        return

    history = rag.get_conversation_history(user_id, limit=20)
    if not history:
        print("No conversation history found.")
        return

    print(f"\n=== Conversation History for {user_id} (last {len(history)}) ===")
    for item in history:
        timestamp = item.get("timestamp", "?")
        question = item.get("question", "")
        answer = item.get("answer", "")
        print(f"[{timestamp}] Q: {question}")
        print(f"             A: {answer}")


while True:
    print("\n[1] Register user")
    print("[2] Identify + ask question")
    print("[3] List users")
    print("[4] Delete user")
    print("[5] Show conversation history")
    print("[6] Exit")

    choice = input("\nEnter choice: ").strip()

    if choice == "1":
        name = input("Enter name: ").strip()
        if name:
            system.register_user(name)
        else:
            print("Name cannot be empty.")

    elif choice == "2":
        ask_question_flow()

    elif choice == "3":
        system.list_users()

    elif choice == "4":
        delete_user_flow()

    elif choice == "5":
        show_history_flow()

    elif choice == "6":
        system.cleanup()
        break

    else:
        print("Invalid choice.")
