import os, re
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from azure.storage.blob import BlobServiceClient, ContentSettings

# --- Config from environment ---
IMAGES_CONTAINER = os.getenv("IMAGES_CONTAINER", "lanternfly-images")
STORAGE_ACCOUNT_URL = os.getenv("STORAGE_ACCOUNT_URL")
CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING")  # for local dev

# --- Connect to Blob Storage ---
if CONN_STR:
    bsc = BlobServiceClient.from_connection_string(CONN_STR)
elif STORAGE_ACCOUNT_URL and os.getenv("AZURE_STORAGE_SAS_TOKEN"):
    bsc = BlobServiceClient(account_url=STORAGE_ACCOUNT_URL, credential=os.getenv("AZURE_STORAGE_SAS_TOKEN"))
elif STORAGE_ACCOUNT_URL:
    bsc = BlobServiceClient(account_url=STORAGE_ACCOUNT_URL)
else:
    raise SystemExit("Missing STORAGE_ACCOUNT_URL or AZURE_STORAGE_CONNECTION_STRING")

cc = bsc.get_container_client(IMAGES_CONTAINER)

app = Flask(__name__)

def sanitize_filename(name: str) -> str:
    # Keep letters, numbers, dot, dash, underscore; strip leading dots/underscores
    base = re.sub(r"[^a-zA-Z0-9._-]+", "_", name).strip("._")
    return base or "upload"

@app.post("/api/v1/upload")
def upload():
    if "file" not in request.files:
        return jsonify(ok=False, error="missing file"), 400
    f = request.files["file"]
    if not f or f.filename == "":
        return jsonify(ok=False, error="empty filename"), 400
    if not (f.mimetype or "").startswith("image/"):
        return jsonify(ok=False, error="only image/* allowed"), 415

    # enforce 10 MB max
    f.seek(0, 2); size = f.tell(); f.seek(0)
    if size > 10 * 1024 * 1024:
        return jsonify(ok=False, error="file too large (>10MB)"), 413

    safe = sanitize_filename(f.filename)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    blob_name = f"{stamp}-{safe}"

    bc = cc.get_blob_client(blob_name)
    bc.upload_blob(f.read(), overwrite=True,
                   content_settings=ContentSettings(content_type=f.mimetype))

    return jsonify(ok=True, url=f"{cc.url}/{blob_name}")

@app.get("/api/v1/gallery")
def gallery():
    urls = [f"{cc.url}/{b.name}" for b in cc.list_blobs()]
    urls.sort(reverse=True)  # newest first by prefix timestamp
    return jsonify(ok=True, gallery=urls)

@app.get("/api/v1/health")
def health():
    try:
        next(iter(cc.list_blobs()), None)
        return jsonify(ok=True), 200
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.get("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
