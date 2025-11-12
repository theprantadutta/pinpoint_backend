"""Quick script to check notes in database for a specific user"""
import sys
from app.database import SessionLocal
from app.models.note import EncryptedNote
from sqlalchemy import func

def check_user_notes(user_id: str):
    db = SessionLocal()
    try:
        # Count total notes for user
        total_count = db.query(func.count(EncryptedNote.id)).filter(
            EncryptedNote.user_id == user_id
        ).scalar()

        print(f"\n=== NOTES FOR USER: {user_id} ===")
        print(f"Total notes: {total_count}")

        # Count non-deleted notes
        active_count = db.query(func.count(EncryptedNote.id)).filter(
            EncryptedNote.user_id == user_id,
            EncryptedNote.is_deleted == False
        ).scalar()
        print(f"Active notes (not deleted): {active_count}")

        # Get all notes details
        notes = db.query(EncryptedNote).filter(
            EncryptedNote.user_id == user_id
        ).all()

        print(f"\nNote details:")
        for note in notes:
            print(f"  - ID: {note.id}")
            print(f"    Client Note ID: {note.client_note_id}")
            print(f"    Created: {note.created_at}")
            print(f"    Updated: {note.updated_at}")
            print(f"    Is Deleted: {note.is_deleted}")
            print(f"    Version: {note.version}")
            print(f"    Metadata: {note.note_metadata}")
            print()

    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_notes.py <user_id>")
        sys.exit(1)

    user_id = sys.argv[1]
    check_user_notes(user_id)
