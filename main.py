import threading
from typing import Dict, List, Optional

import numpy as np
import whisper

from biometric_memory_system import BiometricMemorySystem, SystemConfig
from conversation_store import ConversationStore
from conversation_summarizer import ConversationSummarizer


print("[STARTUP] Loading Whisper STT...")
stt_model = whisper.load_model("base")


def transcribe(audio_buffer: List[bytes]) -> str:
    if not audio_buffer:
        return ""

    audio_data = b"".join(audio_buffer)
    audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
    result = stt_model.transcribe(audio_array, language="en")
    return result["text"].strip()


print("[STARTUP] Loading biometric system...")
config = SystemConfig()
system = BiometricMemorySystem(config)
conversation_store = ConversationStore()
conversation_summarizer = ConversationSummarizer()
print("[STARTUP] All systems ready\n")


def format_user_label(user: Dict) -> str:
    return f"{user.get('name', 'Unknown')} [{user.get('user_id', '?')}]"


def get_registered_users() -> List[Dict]:
    return system.db.list_users()


def find_registered_user_by_name(name: str) -> Optional[Dict]:
    normalized_name = name.strip().lower()
    for user in get_registered_users():
        if user.get("name", "").strip().lower() == normalized_name:
            return user
    return None


def prompt_for_user_id_by_name(prompt_text: str) -> Optional[str]:
    users = get_registered_users()
    if not users:
        print("No users found.")
        return None

    print()
    for index, user in enumerate(users, start=1):
        registered_at = user.get("registered_at", "unknown")
        print(f"[{index}] {format_user_label(user)} ({registered_at})")

    selection = input(f"{prompt_text} ").strip()
    if not selection:
        return None

    if selection.isdigit():
        selection_index = int(selection)
        if 1 <= selection_index <= len(users):
            return users[selection_index - 1].get("user_id")

    exact_matches = [
        user for user in users
        if user.get("name", "").strip().lower() == selection.lower()
    ]
    if len(exact_matches) == 1:
        return exact_matches[0].get("user_id")
    if len(exact_matches) > 1:
        print("Multiple users share that name. Please select by number.")
        return None

    for user in users:
        if user.get("user_id") == selection:
            return user.get("user_id")

    return None


def print_history_summary(user_id: str) -> None:
    entries = conversation_store.get_history(user_id, limit=None)
    if not entries:
        print("\n[CONTEXT] No prior memories are stored for this user yet.")
        return

    summary = conversation_summarizer.summarize(entries)
    print(f"\n[CONTEXT] {summary}")


def register_user_flow() -> None:
    name = input("Enter name: ").strip()
    if not name:
        print("Name cannot be empty.")
        return

    existing_user = find_registered_user_by_name(name)
    if existing_user:
        print(f"[INFO] User already exists: {format_user_label(existing_user)}")
        return

    success = system.register_user(name)
    if not success:
        return

    user_id = system.last_registered_user_id
    if not user_id:
        print("[WARNING] Registration succeeded but no user_id was returned.")
        return
    print(f"[INFO] Registered user: {user_id}")


def identify_user_flow() -> None:
    print("\n[STEP 1] Look at camera (5 seconds)...")
    result = system.verify_user(face_only=True)

    if not result or not result.get("verified"):
        print("This appears to be a new or unrecognized person. Please register first.")
        return

    user_id = result["identity"]
    display_name = result.get("name") or user_id
    print(f"[STEP 2] Verified: {display_name} [{user_id}] ({result['confidence']})")

    print_history_summary(user_id)


def add_memories_flow() -> None:
    user_id = prompt_for_user_id_by_name("Enter user number or exact name to add memories for:")
    if not user_id:
        print("Invalid user selection.")
        return

    print("\n[STEP 1] Speak now to record a memory (7 seconds)...")
    system.voice_processor.clear()
    system.running = True
    audio_thread = threading.Thread(target=system._audio_worker, args=(7,))
    audio_thread.start()
    audio_thread.join()
    system.running = False

    transcript = transcribe(system.voice_processor.audio_buffer)
    if not transcript:
        print("[INFO] No speech captured for this memory.")
        return

    conversation_store.store_utterance(user_id, transcript, source="memory")
    print(f"[INFO] Stored memory for {user_id}")
    print(f"[INFO] Captured memory: {transcript}")


def delete_user_flow() -> None:
    user_id = prompt_for_user_id_by_name("Enter user number or exact name to delete:")
    if not user_id:
        print("Invalid user selection.")
        return

    confirmation = input(f"Type DELETE to remove '{user_id}' from the system: ").strip()
    if confirmation != "DELETE":
        print("Delete cancelled.")
        return

    biometric_deleted = system.delete_user(user_id)
    history_deleted = conversation_store.delete_history(user_id)

    if biometric_deleted:
        print(f"[INFO] Deleted biometric records for {user_id}")
    if history_deleted:
        print(f"[INFO] Deleted conversation history for {user_id}")
    else:
        print(f"[INFO] No conversation history found for {user_id}")


while True:
    print("\n[1] Register user")
    print("[2] Identify user and fetch their memories")
    print("[3] Add memories for existing user")
    print("[4] Show all users stored")
    print("[5] Delete user by name")
    print("[6] Exit")

    choice = input("\nEnter choice: ").strip()

    if choice == "1":
        register_user_flow()

    elif choice == "2":
        identify_user_flow()

    elif choice == "3":
        add_memories_flow()

    elif choice == "4":
        system.list_users()

    elif choice == "5":
        delete_user_flow()

    elif choice == "6":
        system.cleanup()
        break

    else:
        print("Invalid choice.")
