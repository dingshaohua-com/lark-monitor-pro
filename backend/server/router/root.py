from fastapi import APIRouter

router = APIRouter(tags=["root"])

@router.get("/home")
async def home():
    return {"message": "i am home"}