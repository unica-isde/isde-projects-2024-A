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
from io import BytesIO
import base64
from PIL import Image
import magic

from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
         {
            "request": request,
            "images": list_images(),
            "models": Configuration.models,
             #little modification for possibility of change default image
            "selected_image": "n07714571_head_cabbage.JPEG",  # <--- CHANGE Def image HERE
            "selected_model": Configuration.models[0],  # pick a different default model
        },
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

#4-upload-image-button
@app.get("/custom_classifications")
def create_classify(request: Request):
    """
    Renders the selection page for uploading and classifying a custom image.

    Args:
        request (Request): The current HTTP request.

    Returns:
        TemplateResponse: Rendered HTML page with the model selection form.
    """
    return templates.TemplateResponse(
        "custom_classification_select.html",
        {
            "request": request,
            "models": Configuration.models
        },
    )


@app.post("/custom_classifications")
async def upload_file(file: UploadFile, request: Request):
    """
    Handles the upload of an image file and performs classification using the selected model.

    Args:
        file (UploadFile): The image file provided by the user.
        request (Request): The incoming HTTP request.

    Returns:
        TemplateResponse: A rendered template showing the classification results.
    """
    try:
        # Read the uploaded file content
        file_content = await file.read()

        # Detect the MIME type of the uploaded file
        mime = magic.Magic(mime=True)
        file_type = mime.from_buffer(file_content)

        # Ensure the uploaded file is an image
        if not file_type.startswith("image"):
            raise ValueError("The uploaded file is not a valid image.")

        # Load the image from memory
        image_buffer = BytesIO(file_content)
        image = Image.open(image_buffer)

        # Convert the image to PNG format and store it in memory
        png_stream = BytesIO()
        image.save(png_stream, format="PNG")

        # Encode the image in base64 to be used in HTML
        encoded_image = base64.b64encode(png_stream.getvalue()).decode("utf-8")
        data_url = f"data:image/png;base64,{encoded_image}"

        # Load selected model and perform classification
        form = ClassificationForm(request)
        await form.load_data()
        model_id = form.model_id
        classification_scores = classify_image(
            model_id=model_id, img_id=None, custom_img_id=image
        )

        # Render the classification results
        return templates.TemplateResponse(
            "custom_classification_output.html",
            {
                "request": request,
                "image_id": data_url,
                "classification_scores": json.dumps(classification_scores),
            },
        )
    except Exception as e:
        return {"error": f"An error occurred during the image upload: {str(e)}"}

# 3-download-results-button
# New endpoint: Download JSON results
@app.get("/download/json")
def download_json(image_id: str, model_id: str):
    """
    Downloads the classification results as a JSON file.
    Expects query parameters for image_id and model_id.
    """
    classification_scores = classify_image(model_id=model_id, img_id=image_id)
    headers = {"Content-Disposition": "attachment; filename=results.json"}
    return JSONResponse(content=classification_scores, headers=headers)


# New endpoint: Download PNG plot of top 5 classification scores
@app.get("/download/plot")
def download_plot(image_id: str, model_id: str):
    """
    Downloads a PNG file containing a bar chart of the top 5 classification scores.
    Expects query parameters for image_id and model_id.
    """
    classification_scores = classify_image(model_id=model_id, img_id=image_id)

    # Convert list of pairs to dictionary
    classification_dict = dict(classification_scores)

    # Sort and select top 5
    sorted_items = sorted(classification_dict.items(), key=lambda x: x[1], reverse=True)[:5]
    labels, scores = zip(*sorted_items) if sorted_items else ([], [])

    # Create a bar chart using Matplotlib
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(labels, scores)
    ax.set_title("Top 5 Classification Scores")
    ax.set_xlabel("Class")
    ax.set_ylabel("Score")

    # Save the plot to an in-memory buffer
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)

    headers = {"Content-Disposition": "attachment; filename=results_plot.png"}
    return StreamingResponse(buf, media_type="image/png", headers=headers)

# The application can be run with a command such as:
# uvicorn main:app --reload

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
