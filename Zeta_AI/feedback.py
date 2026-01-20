from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import datetime
import json

router = APIRouter()

# Stockage simple sur disque (à remplacer par DB réelle)
FEEDBACK_FILE = "feedback_store.jsonl"

class FeedbackRequest(BaseModel):
    company_id: str
    user_id: str
    question: str
    response: str
    score: int  # 1 (mauvais) à 5 (excellent)
    comment: str = ""
    timestamp: str = None

@router.post("/feedback")
def submit_feedback(feedback: FeedbackRequest):
    feedback.timestamp = datetime.datetime.utcnow().isoformat()
    try:
        with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(feedback.dict(), ensure_ascii=False) + "\n")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
