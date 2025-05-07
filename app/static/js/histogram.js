document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("histogram-form");

    form.addEventListener("submit", function (event) {
        event.preventDefault();

        const imageId = document.getElementById("image_id").value;
        if (!imageId) {
            alert("Please select an image.");
            return;
        }

        fetch(`/histogram/json?image_id=${imageId}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert("Error: " + data.error);
                    return;
                }

                document.getElementById("selected-image").src = `/static/imagenet_subset/${data.image_id}`;
                document.getElementById("selected-image").style.display = "block";

                renderHistogram(data.histogram);
                document.getElementById("histogram-results").style.display = "block";
            });

        document.getElementById("histogram-image").src = `/histogram/image?image_id=${imageId}`;
        document.getElementById("histogram-image").style.display = "block";
    });

    function renderHistogram(histogramData) {
        const ctx = document.getElementById("histogramChart").getContext("2d");

        if (window.histogramChart instanceof Chart) {
            window.histogramChart.destroy();
        }

        window.histogramChart = new Chart(ctx, {
            type: "bar",
            data: {
                labels: Array.from({ length: 256 }, (_, i) => i),
                datasets: [{
                    label: "Pixel Intensity",
                    data: histogramData,
                    backgroundColor: "black"
                }]
            },
            options: {
                scales: {
                    x: { title: { display: true, text: "Pixel Value" } },
                    y: { title: { display: true, text: "Frequency" } }
                }
            }
        });
    }
});
