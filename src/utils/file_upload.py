"""
File upload and storage utilities.

✅ BINARY STORAGE: Primary methods for database storage (no disk)
✅ FILESYSTEM STORAGE: Legacy methods for backward compatibility
✅ DATA URI CONVERSION: For Groq Vision API integration
✅ IMAGE OPTIMIZATION: In-memory compression and resizing
✅ VALIDATION: File type, size, and image format validation

Architecture:
- Binary storage methods (NEW): For production deployment on Render/Heroku
- Filesystem methods (LEGACY): For local development and backward compatibility
"""

import os
import uuid
import shutil
import base64
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
from fastapi import UploadFile
from PIL import Image

from src.config.settings import settings
from src.utils.exceptions import InvalidFileTypeError, FileTooLargeError, FileUploadError
from src.utils.validators import validate_file_extension
from src.utils.logger import app_logger


class FileUploadHandler:
    """Handler for file uploads (binary database + filesystem storage)"""
    
    def __init__(self):
        """Initialize file upload handler"""
        # Filesystem settings (for legacy methods)
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.max_file_size = settings.MAX_FILE_SIZE
        self.allowed_extensions = settings.ALLOWED_IMAGE_EXTENSIONS
        
        # Binary storage settings (for new methods)
        self.max_image_size_mb = 10  # 10 MB limit for binary storage
        self.allowed_mimetypes = {
            'image/jpeg', 'image/jpg', 'image/png', 
            'image/gif', 'image/webp', 'image/bmp'
        }
        
        # Optimization settings
        self.max_width = 1920
        self.max_height = 1920
        self.jpeg_quality = 85
        self.thumbnail_size = (200, 200)
        self.thumbnail_quality = 70
        
        # Create upload directory if it doesn't exist (for filesystem methods)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    # ==================== BINARY DATABASE STORAGE METHODS (NEW - PRIMARY) ====================
    
    async def read_image_bytes(
        self,
        file: UploadFile,
        validate: bool = True
    ) -> Tuple[bytes, str, int, str]:
        """
        Read uploaded image as bytes for database storage (NO DISK USAGE).
        
        This is the PRIMARY method for production deployment.
        Images are stored as BYTEA in PostgreSQL, not as files.
        
        Args:
            file: FastAPI UploadFile object
            validate: Whether to validate file type and size
        
        Returns:
            Tuple of (image_bytes, mimetype, size_bytes, original_filename)
        
        Raises:
            InvalidFileTypeError: If file type is not allowed
            FileTooLargeError: If file size exceeds limit
            FileUploadError: If read fails
        
        Example:
            >>> image_bytes, mimetype, size, filename = await file_upload_handler.read_image_bytes(file)
            >>> # Store in database:
            >>> complaint.image_data = image_bytes
            >>> complaint.image_mimetype = mimetype
        """
        try:
            # Read file contents as bytes
            image_bytes = await file.read()
            file_size = len(image_bytes)
            
            # Get MIME type
            mimetype = file.content_type or self._guess_mimetype(file.filename)
            
            # Get filename
            filename = file.filename or 'image.jpg'
            
            # Validate if requested
            if validate:
                await self.validate_image_bytes(image_bytes, mimetype, file_size)
            
            app_logger.info(
                "Image read as bytes",
                extra={
                    "uploaded_filename": filename,
                    "size_bytes": file_size,
                    "mimetype": mimetype
                }
            )
            
            return image_bytes, mimetype, file_size, filename
            
        except (InvalidFileTypeError, FileTooLargeError):
            raise
        except Exception as e:
            app_logger.error(f"Failed to read image bytes: {e}")
            raise FileUploadError(f"Failed to read image: {str(e)}")
    
    async def validate_image_bytes(
        self,
        image_bytes: bytes,
        mimetype: str,
        file_size: Optional[int] = None,
        max_size_mb: Optional[int] = None
    ) -> bool:
        """
        Validate image bytes without saving to disk.
        
        Args:
            image_bytes: Image data as bytes
            mimetype: MIME type (e.g., "image/jpeg")
            file_size: Optional file size (will calculate if None)
            max_size_mb: Optional max size in MB (uses default if None)
        
        Returns:
            True if valid
        
        Raises:
            InvalidFileTypeError: If MIME type not allowed
            FileTooLargeError: If file too large
            FileUploadError: If image is corrupted/invalid
        
        Example:
            >>> is_valid = await file_upload_handler.validate_image_bytes(
            ...     image_bytes, "image/jpeg"
            ... )
        """
        # Check MIME type
        if mimetype not in self.allowed_mimetypes:
            raise InvalidFileTypeError(list(self.allowed_mimetypes))
        
        # Check file size
        if file_size is None:
            file_size = len(image_bytes)
        
        max_size = (max_size_mb or self.max_image_size_mb) * 1024 * 1024
        if file_size > max_size:
            raise FileTooLargeError(max_size)
        
        # Validate image can be opened and is not corrupted
        try:
            img = Image.open(BytesIO(image_bytes))
            img.verify()  # Verify it's a valid image
            
            app_logger.info(
                "Image validation passed",
                extra={
                    "size_bytes": file_size,
                    "mimetype": mimetype
                }
            )
            
            return True
            
        except Exception as e:
            app_logger.error(f"Invalid image data: {e}")
            raise FileUploadError(f"Invalid or corrupted image: {str(e)}")
    
    async def optimize_image_bytes(
        self,
        image_bytes: bytes,
        mimetype: str,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
        quality: Optional[int] = None
    ) -> Tuple[bytes, int]:
        """
        Optimize image bytes in memory (resize + compress).
        
        This reduces database storage and improves performance.
        
        Args:
            image_bytes: Original image bytes
            mimetype: MIME type
            max_width: Optional max width (uses default if None)
            max_height: Optional max height (uses default if None)
            quality: Optional JPEG quality 1-100 (uses default if None)
        
        Returns:
            Tuple of (optimized_bytes, new_size_bytes)
        
        Example:
            >>> optimized_bytes, size = await file_upload_handler.optimize_image_bytes(
            ...     image_bytes, "image/jpeg"
            ... )
            >>> # Size reduced from 2 MB to 500 KB
        """
        try:
            # Set defaults
            max_width = max_width or self.max_width
            max_height = max_height or self.max_height
            quality = quality or self.jpeg_quality
            
            # Open image from bytes
            img = Image.open(BytesIO(image_bytes))
            original_size = img.size
            
            # Convert RGBA to RGB (for JPEG compatibility)
            if img.mode == "RGBA":
                rgb_img = Image.new("RGB", img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3])
                img = rgb_img
            elif img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            
            # Resize if too large
            resized = False
            if img.width > max_width or img.height > max_height:
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                resized = True
            
            # Save optimized to bytes (always JPEG for consistency)
            output = BytesIO()
            img.save(output, format="JPEG", optimize=True, quality=quality)
            optimized_bytes = output.getvalue()
            optimized_size = len(optimized_bytes)
            
            # Calculate compression ratio
            compression_ratio = (1 - optimized_size / len(image_bytes)) * 100
            
            app_logger.info(
                f"Image optimized: {len(image_bytes)} -> {optimized_size} bytes "
                f"({compression_ratio:.1f}% reduction)"
                + (f", resized from {original_size} to {img.size}" if resized else "")
            )
            
            return optimized_bytes, optimized_size
            
        except Exception as e:
            app_logger.warning(f"Image optimization failed: {e}, using original")
            return image_bytes, len(image_bytes)
    
    async def create_thumbnail(
        self,
        image_bytes: bytes,
        size: Optional[Tuple[int, int]] = None,
        quality: Optional[int] = None
    ) -> Tuple[bytes, int]:
        """
        Create thumbnail from image bytes.
        
        Args:
            image_bytes: Original image bytes
            size: Thumbnail size (width, height), defaults to (200, 200)
            quality: JPEG quality 1-100, defaults to 70
        
        Returns:
            Tuple of (thumbnail_bytes, size_bytes)
        
        Example:
            >>> thumb_bytes, thumb_size = await file_upload_handler.create_thumbnail(
            ...     image_bytes, size=(150, 150)
            ... )
        """
        try:
            size = size or self.thumbnail_size
            quality = quality or self.thumbnail_quality
            
            # Open image
            img = Image.open(BytesIO(image_bytes))
            
            # Convert to RGB
            if img.mode == "RGBA":
                rgb_img = Image.new("RGB", img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3])
                img = rgb_img
            elif img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            
            # Create thumbnail (maintains aspect ratio)
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Save to bytes
            output = BytesIO()
            img.save(output, format="JPEG", optimize=True, quality=quality)
            thumbnail_bytes = output.getvalue()
            
            app_logger.info(
                f"Thumbnail created: {img.size} ({len(thumbnail_bytes)} bytes)"
            )
            
            return thumbnail_bytes, len(thumbnail_bytes)
            
        except Exception as e:
            app_logger.error(f"Thumbnail creation failed: {e}")
            raise FileUploadError(f"Failed to create thumbnail: {str(e)}")
    
    def bytes_to_data_uri(
        self,
        image_bytes: bytes,
        mimetype: str
    ) -> str:
        """
        Convert image bytes to base64 data URI.
        
        Used for Groq Vision API which requires data URIs.
        
        Args:
            image_bytes: Image bytes
            mimetype: MIME type (e.g., "image/jpeg")
        
        Returns:
            Data URI string (data:image/jpeg;base64,...)
        
        Example:
            >>> data_uri = file_upload_handler.bytes_to_data_uri(
            ...     image_bytes, "image/jpeg"
            ... )
            >>> # Returns: "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
        """
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        return f"data:{mimetype};base64,{base64_image}"
    
    def data_uri_to_bytes(
        self,
        data_uri: str
    ) -> Tuple[bytes, str]:
        """
        Convert data URI back to bytes.
        
        Args:
            data_uri: Data URI string (data:image/jpeg;base64,...)
        
        Returns:
            Tuple of (image_bytes, mimetype)
        
        Raises:
            FileUploadError: If data URI format is invalid
        
        Example:
            >>> image_bytes, mimetype = file_upload_handler.data_uri_to_bytes(
            ...     "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
            ... )
        """
        try:
            # Parse data URI: data:image/jpeg;base64,ABC123...
            if not data_uri.startswith("data:"):
                raise ValueError("Invalid data URI format")
            
            header, encoded = data_uri.split(",", 1)
            mimetype = header.split(";")[0].split(":")[1]
            image_bytes = base64.b64decode(encoded)
            
            return image_bytes, mimetype
            
        except Exception as e:
            app_logger.error(f"Failed to decode data URI: {e}")
            raise FileUploadError(f"Invalid data URI format: {str(e)}")
    
    def get_image_metadata(
        self,
        image_bytes: bytes
    ) -> dict:
        """
        Get image metadata from bytes.
        
        Args:
            image_bytes: Image bytes
        
        Returns:
            Dictionary with width, height, format, mode, size_bytes
        
        Example:
            >>> metadata = file_upload_handler.get_image_metadata(image_bytes)
            >>> # {'width': 1920, 'height': 1080, 'format': 'JPEG', ...}
        """
        try:
            with Image.open(BytesIO(image_bytes)) as img:
                return {
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode,
                    "size_bytes": len(image_bytes)
                }
        except Exception as e:
            app_logger.warning(f"Failed to get image metadata: {e}")
            return {"size_bytes": len(image_bytes)}
    
    # ==================== FILESYSTEM STORAGE METHODS (LEGACY - FOR BACKWARD COMPATIBILITY) ====================
    
    async def save_image(
        self,
        file: UploadFile,
        subfolder: Optional[str] = None
    ) -> Tuple[str, dict]:
        """
        Save uploaded image file to filesystem.
        
        ⚠️ LEGACY METHOD: For backward compatibility only.
        ⚠️ NOT recommended for production (files lost on server restart).
        ⚠️ Use read_image_bytes() for production deployment instead.
        
        Args:
            file: Uploaded file
            subfolder: Optional subfolder name
        
        Returns:
            Tuple of (file_path, metadata)
        
        Raises:
            InvalidFileTypeError: If file type is not allowed
            FileTooLargeError: If file size exceeds limit
            FileUploadError: If upload fails
        """
        # Validate file extension
        is_valid, error_msg = validate_file_extension(
            file.filename,
            self.allowed_extensions
        )
        if not is_valid:
            raise InvalidFileTypeError(self.allowed_extensions)
        
        # Check file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to start
        
        if file_size > self.max_file_size:
            raise FileTooLargeError(self.max_file_size)
        
        # Generate unique filename
        ext = file.filename.rsplit(".", 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{ext}"
        
        # Determine save path
        if subfolder:
            save_dir = self.upload_dir / subfolder
            save_dir.mkdir(parents=True, exist_ok=True)
        else:
            save_dir = self.upload_dir
        
        file_path = save_dir / unique_filename
        
        try:
            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Get image metadata
            metadata = self._get_image_metadata_from_path(file_path)
            
            # Optimize image if needed
            await self._optimize_image_filesystem(file_path)
            
            # Return relative path for storage
            relative_path = str(file_path.relative_to(self.upload_dir.parent))
            
            app_logger.info(
                f"Image saved to filesystem (LEGACY): {relative_path}",
                extra={"file_path": relative_path, "size": file_size}
            )
            
            return relative_path, metadata
            
        except Exception as e:
            # Cleanup on error
            if file_path.exists():
                file_path.unlink()
            raise FileUploadError(f"Failed to save file: {str(e)}")
    
    def _get_image_metadata_from_path(self, file_path: Path) -> dict:
        """Get image metadata from file path (legacy method)"""
        try:
            with Image.open(file_path) as img:
                return {
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode,
                    "size_bytes": file_path.stat().st_size
                }
        except Exception:
            return {}
    
    async def _optimize_image_filesystem(self, file_path: Path):
        """Optimize image on filesystem (legacy method)"""
        try:
            with Image.open(file_path) as img:
                # Convert RGBA to RGB if needed
                if img.mode == "RGBA":
                    rgb_img = Image.new("RGB", img.size, (255, 255, 255))
                    rgb_img.paste(img, mask=img.split()[3])
                    img = rgb_img
                
                # Resize if too large
                if img.width > self.max_width or img.height > self.max_height:
                    img.thumbnail((self.max_width, self.max_height), Image.Resampling.LANCZOS)
                
                # Save with optimization
                img.save(file_path, optimize=True, quality=self.jpeg_quality)
                
        except Exception as e:
            app_logger.warning(
                f"Filesystem image optimization failed for {file_path.name}: {e}"
            )
    
    def delete_file(self, file_path: str) -> bool:
        """Delete uploaded file from filesystem (legacy method)"""
        try:
            path = Path(file_path)
            if not path.is_absolute():
                path = self.upload_dir.parent / file_path
            
            if path.exists():
                path.unlink()
                return True
        except Exception:
            pass
        return False
    
    def get_file_url(self, file_path: str, base_url: str = "") -> str:
        """Get URL for uploaded file (legacy method)"""
        return f"{base_url}/{file_path}".replace("\\", "/")
    
    # ==================== UTILITY METHODS ====================
    
    def _guess_mimetype(self, filename: str) -> str:
        """
        Guess MIME type from filename extension.
        
        Args:
            filename: File name
        
        Returns:
            MIME type string
        """
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        mime_types = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
            "bmp": "image/bmp"
        }
        return mime_types.get(ext, "image/jpeg")


# Global file upload handler instance
file_upload_handler = FileUploadHandler()


__all__ = ["FileUploadHandler", "file_upload_handler"]
