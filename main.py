
import json
import base64
import io
from pathlib import Path
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image, ImageEnhance
from app.config import Configuration
from app.forms.classification_form import ClassificationForm
from app.ml.classification_utils import classify_image
from app.utils import list_images

app = FastAPI()
config = Configuration()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Path for image folder
IMAGE_FOLDER = Path(config.image_folder_path)


@app.get("/info")
def info() -> dict[str, list[str]]:
    """Returns a dictionary with the list of models and
    the list of available image files."""
    list_of_images = list_images()
    list_of_models = Configuration.models
    data = {"models": list_of_models, "images": list_of_images}
    return data


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """The home page of the service."""
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/classifications")
def create_classify(request: Request):
    return templates.TemplateResponse(
        "classification_select.html",
        {"request": request, "images": list_images(), "models": Configuration.models},
    )


#add_modification by Lu
@app.get("/transform", response_class=HTMLResponse)
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


@app.post("/transform", response_class=HTMLResponse)
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

    if not image_path.is_file():
        return templates.TemplateResponse("transform.html", {
            "request": request,
            "error": f"Image '{image_name}' not found.",
            "images": list_images()
        })

    try:
        original_img = Image.open(image_path)
    except Exception as e:
        return templates.TemplateResponse("transform.html", {
            "request": request,
            "error": f"Could not open image: {e}",
            "images": list_images()
        })

    transformed_img = ImageEnhance.Color(original_img).enhance(color)
    transformed_img = ImageEnhance.Brightness(transformed_img).enhance(brightness)
    transformed_img = ImageEnhance.Contrast(transformed_img).enhance(contrast)
    transformed_img = ImageEnhance.Sharpness(transformed_img).enhance(sharpness)

    def img_to_base64(img):
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    original_b64 = img_to_base64(original_img)
    transformed_b64 = img_to_base64(transformed_img)

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
