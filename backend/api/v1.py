from fastapi import APIRouter

router = APIRouter(prefix="/v1")

@router.get("/health")
def health_check():
    return {"status": "healthy"}