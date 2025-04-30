import base64
import io
from pathlib import Path
from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from PIL import Image, ImageEnhance
from app.utils import list_images
from app.config import Configuration

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
IMAGE_FOLDER = Path(Configuration().image_folder_path)

@router.get("/transform", response_class=HTMLResponse)
def show_transform_form(request: Request):
    # Render the image transformation form with a list of available images
    available_images = list_images()
    return templates.TemplateResponse("transform.html", {
        "request": request,
        "images": available_images
    })

@router.post("/transform", response_class=HTMLResponse)
async def apply_transformations(
    request: Request,
    image_name: str = Form(""),
    color: float = Form(1.0),
    brightness: float = Form(1.0),
    contrast: float = Form(1.0),
    sharpness: float = Form(1.0),
    image_file: UploadFile = File(None),
):
    # Load the image from upload or selection
    if image_file and image_file.filename:
        try:
            contents = await image_file.read()
            original_img = Image.open(io.BytesIO(contents))
            image_format = original_img.format or "PNG"  # Default to PNG if format not detected
        except Exception as e:
            return templates.TemplateResponse("transform.html", {
                "request": request,
                "error": f"Failed to load uploaded image: {e}",
                "images": list_images()
            })
        image_name_display = image_file.filename
    elif image_name:
        image_path = IMAGE_FOLDER / image_name
        if not image_path.is_file():
            return templates.TemplateResponse("transform.html", {
                "request": request,
                "error": f"Image '{image_name}' not found.",
                "images": list_images()
            })
        try:
            original_img = Image.open(image_path)
            image_format = original_img.format or "PNG"
        except Exception as e:
            return templates.TemplateResponse("transform.html", {
                "request": request,
                "error": f"Could not open image: {e}",
                "images": list_images()
            })
        image_name_display = image_name
    else:
        # No image selected or uploaded
        return templates.TemplateResponse("transform.html", {
            "request": request,
            "error": "Select an image or upload a new one.",
            "images": list_images()
        })

    # Apply image enhancements in sequence
    transformed_img = ImageEnhance.Color(original_img).enhance(color)
    transformed_img = ImageEnhance.Brightness(transformed_img).enhance(brightness)
    transformed_img = ImageEnhance.Contrast(transformed_img).enhance(contrast)
    transformed_img = ImageEnhance.Sharpness(transformed_img).enhance(sharpness)

    # Convert a PIL image to base64 for rendering or downloading
    def img_to_base64(img, fmt):
        buf = io.BytesIO()
        # Convert RGBA to RGB if format doesn't support transparency
        if fmt.upper() == "JPEG" and img.mode == "RGBA":
            img = img.convert("RGB")
        img.save(buf, format=fmt)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    # Convert both original and transformed images to base64
    original_b64 = img_to_base64(original_img, image_format)
    transformed_b64 = img_to_base64(transformed_img, image_format)

    # Use the appropriate file extension for the download
    download_filename = f"transformed_{Path(image_name_display or 'image').stem}.{image_format.lower()}"

    # Render the result page with images and download link
    return templates.TemplateResponse("transform_result.html", {
        "request": request,
        "image_name": image_name_display,
        "original_b64": original_b64,
        "transformed_b64": transformed_b64,
        "download_filename": download_filename,
        "image_format": image_format.lower(),
        "color": color,
        "brightness": brightness,
        "contrast": contrast,
        "sharpness": sharpness,
    })
