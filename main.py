import os
import sys
import json
import io
import cv2
import matplotlib
matplotlib.use('Agg')  # Prevents GUI issues with matplotlib
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Config and app-specific imports
from app.config import Configuration
from app.utils import list_images, IMAGE_FOLDER
from app.forms.classification_form import ClassificationForm
from app.ml.classification_utils import classify_image

# Ensure `app/` is in the import path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))  # Add `app/` to import path

app = FastAPI()
config = Configuration()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


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


@app.post("/classifications")
async def request_classification(request: Request):
    form = ClassificationForm(request)
    await form.load_data()
    image_id = form.image_id
    model_id = form.model_id
    classification_scores = classify_image(model_id=model_id, img_id=image_id)
    return templates.TemplateResponse(
        "classification_output.html",
        {
            "request": request,
            "image_id": image_id,
            "model_id": model_id,
            "classification_scores": json.dumps(classification_scores),
        },
    )

#-----Doris-----
# Register the histogram API routes
#app.include_router(histogram_router) #questa linea se con modifiche in file esterno

@app.get("/histogram", response_class=HTMLResponse, name="get_histogram_page")
def get_histogram_page(request: Request):
    return templates.TemplateResponse(
        "histogram_select.html",
        {
            "request": request,
            "images": list_images()
        }
    )

@app.get("/histogram/json", response_class=JSONResponse)
def get_histogram_json(image_id: str):
    image_path = Path(IMAGE_FOLDER) / image_id
    if not image_path.exists():
        return JSONResponse(status_code=404, content={"error": "Image not found"})

    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    hist = cv2.calcHist([image], [0], None, [256], [0, 256])
    return {
        "image_id": image_id,
        "histogram": hist.flatten().tolist()
    }

@app.get("/histogram/image")
def get_histogram_image(image_id: str):
    image_path = Path(IMAGE_FOLDER) / image_id
    if not image_path.exists():
        return JSONResponse(status_code=404, content={"error": "Image not found"})

    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    hist = cv2.calcHist([image], [0], None, [256], [0, 256])

    plt.figure()
    plt.plot(hist, color='black')
    plt.xlabel('Pixel Value')
    plt.ylabel('Frequency')
    plt.title(f'Histogram of {image_id}')

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()

    return Response(content=buffer.getvalue(), media_type="image/png")