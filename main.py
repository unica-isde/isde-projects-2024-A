import json
import io
import matplotlib.pyplot as plt

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import Configuration
from app.forms.classification_form import ClassificationForm
from app.ml.classification_utils import classify_image
from app.utils import list_images

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
