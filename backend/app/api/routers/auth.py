from fastapi import APIRouter

router = APIRouter()


@router.post("/login")
async def login():
    return {"message": "login endpoint placeholder"}


@router.post("/register")
async def register():
    return {"message": "register endpoint placeholder"}
