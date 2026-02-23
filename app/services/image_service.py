from fastapi import UploadFile
from app.clients.cloudinary_client import CloudinaryClient


class ImageService:
    ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
    MAX_SIZE_MB = 10

    def __init__(self, cloudinary_client: CloudinaryClient):
        self.cloudinary = cloudinary_client

    async def upload_product_photo(self, file: UploadFile, product_id: str) -> dict:
        if file.content_type not in self.ALLOWED_TYPES:
            raise ValueError(f"File type not allowed: {file.content_type}. Use JPEG, PNG, or WebP.")
        return await self.cloudinary.upload_image(file, folder=f"pokemon-store/{product_id}")

    async def delete_product_photo(self, public_id: str) -> bool:
        return await self.cloudinary.delete_image(public_id)
