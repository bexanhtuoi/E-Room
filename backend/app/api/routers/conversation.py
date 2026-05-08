from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_conversations():
    return {"items": [], "message": "conversation list placeholder"}


@router.post("/")
async def create_conversation():
    return {"message": "create conversation placeholder"}
