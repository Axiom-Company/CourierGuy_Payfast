import cloudinary
import cloudinary.uploader
from fastapi import UploadFile
from app.config import get_settings


class CloudinaryClient:
    def __init__(self):
        settings = get_settings()
        cloudinary.config(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
        )

    async def upload_image(self, file: UploadFile, folder: str = "pokemon-store") -> dict:
        contents = await file.read()
        result = cloudinary.uploader.upload(
            contents, folder=folder, resource_type="image",
            transformation=[{"quality": "auto:good", "fetch_format": "auto"}, {"width": 1200, "crop": "limit"}],
        )
        return {"url": result["secure_url"], "public_id": result["public_id"],
                "width": result["width"], "height": result["height"]}

    async def delete_image(self, public_id: str) -> bool:
        result = cloudinary.uploader.destroy(public_id)
        return result.get("result") == "ok"
