import base64
import io
from pathlib import Path
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from PIL import Image, ImageEnhance
from app.utils import list_images
from app.config import Configuration

# Initialize the FastAPI router
router = APIRouter()

# Path to the Jinja2 templates directory
templates = Jinja2Templates(directory="app/templates")

# Path to the folder containing the images
IMAGE_FOLDER = Path(Configuration().image_folder_path)


@router.get("/transform", response_class=HTMLResponse)
def show_transform_form(request: Request):
    """
    Display the image transformation form.
    Loads the list of available images.
    """
    available_images = list_images()
    return templates.TemplateResponse("transform.html", {
        "request": request,
        "images": available_images
    })


@router.post("/transform", response_class=HTMLResponse)
async def apply_transformations(
    request: Request,
    image_name: str = Form(...),
    color: float = Form(1.0),
    brightness: float = Form(1.0),
    contrast: float = Form(1.0),
    sharpness: float = Form(1.0),
):
    """
    Apply the selected transformations to the given image.
    Transformations include color, brightness, contrast, and sharpness adjustments.
    """
    image_path = IMAGE_FOLDER / image_name

    # Check that the file exists
    if not image_path.is_file():
        # If the file doesn't exist, return an error and reload the image list
        return templates.TemplateResponse("transform.html", {
            "request": request,
            "error": f"Image '{image_name}' not found.",
            "images": list_images()
        })

    try:
        # Try to open the image
        original_img = Image.open(image_path)
    except Exception as e:
        # Handle image opening errors
        return templates.TemplateResponse("transform.html", {
            "request": request,
            "error": f"Could not open image: {e}",
            "images": list_images()
        })

    # Apply transformations in sequence: Color -> Brightness -> Contrast -> Sharpness
    transformed_img = ImageEnhance.Color(original_img).enhance(color)
    transformed_img = ImageEnhance.Brightness(transformed_img).enhance(brightness)
    transformed_img = ImageEnhance.Contrast(transformed_img).enhance(contrast)
    transformed_img = ImageEnhance.Sharpness(transformed_img).enhance(sharpness)

    # Utility function to convert a PIL image to base64 for inline HTML rendering
    def img_to_base64(img):
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    # Convert both original and transformed images to base64
    original_b64 = img_to_base64(original_img)
    transformed_b64 = img_to_base64(transformed_img)

    # Render the result page with both images and the transformation parameters
    return templates.TemplateResponse("transform_result.html", {
        "request": request,
        "image_name": image_name,
        "original_b64": original_b64,
        "transformed_b64": transformed_b64,
        "color": color,
        "brightness": brightness,
        "contrast": contrast,
        "sharpness": sharpness,
    })
