from fastapi import APIRouter

router = APIRouter()


@router.get("/me")
async def get_me():
    return {"id": "demo-user", "email": "demo@eroom.local"}
