from typing import Dict, List, Optional

import numpy as np
import whisper

from biometric_memory_system import BiometricMemorySystem, SystemConfig
from conversation_store import ConversationStore


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
print("[STARTUP] All systems ready\n")


def format_user_label(user: Dict) -> str:
    return f"{user.get('name', 'Unknown')} [{user.get('user_id', '?')}]"


def build_user_index(include_history_only: bool = False) -> List[Dict]:
    users = system.db.list_users()
    history_ids = set(conversation_store.list_users())
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


def print_history(user_id: str, limit: int = 20) -> None:
    history = conversation_store.get_history(user_id, limit=limit)
    if not history:
        print("[INFO] No prior conversations stored for this user.")
        return

    print(f"\n=== Previous Conversations for {user_id} (last {len(history)}) ===")
    for entry in history:
        timestamp = entry.get("timestamp", "?")
        source = entry.get("source", "unknown")
        text = entry.get("text", "")
        print(f"[{timestamp}] ({source}) {text}")


def register_user_flow() -> None:
    name = input("Enter name: ").strip()
    if not name:
        print("Name cannot be empty.")
        return

    success = system.register_user(name)
    if not success:
        return

    user_id = system.last_registered_user_id
    if not user_id:
        print("[WARNING] Registration succeeded but no user_id was returned.")
        return

    transcript = transcribe(system.voice_processor.audio_buffer)
    if not transcript:
        print("[INFO] Registration completed, but no speech was captured to store.")
        return

    conversation_store.store_utterance(user_id, transcript, source="register")
    print(f"[INFO] Stored enrollment transcript for {user_id}")
    print(f"[INFO] Captured this session: {transcript}")


def identify_user_flow() -> None:
    print("\n[STEP 1] Look at camera and speak (5 seconds)...")
    result = system.verify_user()

    if not result or not result.get("verified"):
        print("This appears to be a new or unrecognized person. Please register first.")
        return

    user_id = result["identity"]
    display_name = result.get("name") or user_id
    print(f"[STEP 2] Verified: {display_name} [{user_id}] ({result['confidence']})")

    print_history(user_id, limit=20)

    transcript = transcribe(system.voice_processor.audio_buffer)
    if not transcript:
        print("[INFO] No speech captured for this session.")
        return

    conversation_store.store_utterance(user_id, transcript, source="verify")
    print(f"[INFO] Captured this session: {transcript}")


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
    history_deleted = conversation_store.delete_history(user_id)

    if biometric_deleted:
        print(f"[INFO] Deleted biometric records for {user_id}")
    if history_deleted:
        print(f"[INFO] Deleted conversation history for {user_id}")
    else:
        print(f"[INFO] No conversation history found for {user_id}")


def show_history_flow() -> None:
    user_id = prompt_for_user_id("Enter user number or user_id to inspect history:", history_only=True)
    if not user_id:
        print("Invalid user selection.")
        return

    print_history(user_id, limit=20)


while True:
    print("\n[1] Register user")
    print("[2] Identify user + show prior history")
    print("[3] List users")
    print("[4] Delete user")
    print("[5] Show conversation history")
    print("[6] Exit")

    choice = input("\nEnter choice: ").strip()

    if choice == "1":
        register_user_flow()

    elif choice == "2":
        identify_user_flow()

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
