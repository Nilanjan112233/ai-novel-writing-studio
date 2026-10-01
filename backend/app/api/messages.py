from fastapi import APIRouter, HTTPException
from bson import ObjectId
from datetime import datetime
from app.core.database import Database

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.delete("/{message_id}")
async def delete_message(message_id: str):
    """Delete one timeline message."""
    if not ObjectId.is_valid(message_id):
        raise HTTPException(status_code=400, detail="Invalid message ID")

    db = Database.get_db()
    message = await db.timeline_messages.find_one({"_id": ObjectId(message_id)})
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    await db.timeline_messages.delete_one({"_id": ObjectId(message_id)})
    await db.projects.update_one(
        {"_id": message["project_id"]},
        {"$set": {"updated_at": datetime.utcnow()}},
    )
    return {"message": "Message deleted"}
