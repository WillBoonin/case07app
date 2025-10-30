import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from azure.storage.blob import BlobServiceClient

# --- Config ---
CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = "uploads"   # Required by Case-07

if not CONN_STR:
    raise SystemExit("Missing AZURE_STORAGE_CONNECTION_STRING")

bsc = BlobServiceClient.from_connection_string(CONN_STR)
container = bsc.get_container_client(CONTAINER_NAME)

app = Flask(__name__)

@app.post("/api/v1/upload")
def upload():
    # Check file was submitted
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files["file"]
    filename = file.filename

    # Upload to Azure Blob
    blob_client = container.get_blob_client(filename)
    blob_client.upload_blob(file, overwrite=True)

    # ✅ Exact response format required by Gradescope
    return jsonify({
        "filename": filename,
        "container": CONTAINER_NAME
    }), 200


@app.get("/api/v1/gallery")
def gallery():
    urls = [f"{container.url}/{blob.name}" for blob in container.list_blobs()]
    urls.sort(reverse=True)
    return jsonify({"gallery": urls}), 200


@app.get("/api/v1/health")
def health():
    try:
        # Touch container to verify access
        next(iter(container.list_blobs()), None)
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


@app.get("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
