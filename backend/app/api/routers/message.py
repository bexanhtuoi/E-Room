from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_messages():
    return {"items": [], "message": "message list placeholder"}


@router.post("/stream")
async def stream_message():
    return {"message": "stream endpoint placeholder"}
