from io import BytesIO

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.schemas.food_scan import FoodScanAnalysisResponse
from app.schemas.scan import BodyScanAnalysisResponse
from app.services.auth import get_current_user_email
from ml.body_scan.model import analyze_body_image
from ml.food_scan.model import analyze_food_image


router = APIRouter(prefix="/scan", tags=["Scan"])


@router.post("/analyze", response_model=BodyScanAnalysisResponse, status_code=status.HTTP_200_OK)
async def analyze_scan(
    image: UploadFile = File(...),
    body_part: str | None = Form(default=None),
    _: str = Depends(get_current_user_email),
):
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image is empty.",
        )

    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image too large. Please upload an image under 10MB.",
        )

    # Validate by actual bytes because browsers may send generic MIME headers.
    try:
        Image.open(BytesIO(image_bytes)).verify()
    except (UnidentifiedImageError, OSError) as e:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Please upload a valid image file.",
        ) from e

    try:
        result = analyze_body_image(image_bytes, body_part=body_part)
        return BodyScanAnalysisResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not analyze image: {str(e)}",
        ) from e


@router.post("/food/analyze", response_model=FoodScanAnalysisResponse, status_code=status.HTTP_200_OK)
async def analyze_food_scan(
    image: UploadFile = File(...),
    meal_type: str | None = Form(default=None),
    hint: str | None = Form(default=None),
    _: str = Depends(get_current_user_email),
):
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image is empty.",
        )

    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image too large. Please upload an image under 10MB.",
        )

    try:
        Image.open(BytesIO(image_bytes)).verify()
    except (UnidentifiedImageError, OSError) as e:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Please upload a valid image file.",
        ) from e

    try:
        result = analyze_food_image(image_bytes, meal_type=meal_type, hint=hint)
        return FoodScanAnalysisResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not analyze food image: {str(e)}",
        ) from e
