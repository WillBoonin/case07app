from flask import Flask, jsonify, render_template
from azure.storage.blob import BlobServiceClient, ContentSettings, PublicAccess
import os

app = Flask(__name__)

# Get Azure Storage connection string from environment variable
connect_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")


blob_service_client = None
if connect_str:
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
else:
    print("⚠️ Missing Azure Storage connection string!")

cc=blob_service_client.get_container_client("uploads") if blob_service_client else None

@app.get("/")
def index():
    return render_template("index.html")


@app.route('/api/v1/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

@app.get("/api/v1/gallery")
def gallery():
    urls = [f"{cc.url}/{b.name}" for b in cc.list_blobs()]
    return jsonify(ok=True, gallery=urls)


@app.route('/api/v1/upload', methods=['POST'])
def upload():
    try:
        if not blob_service_client:
            return jsonify({"error": "Missing Azure connection string"}), 500

        container_name = "uploads"
        container_client = blob_service_client.get_container_client(container_name)
        try:
            container_client.create_container()
        except Exception:
            pass  # Ignore "already exists"

        blob_name = "test_upload.txt"
        blob_content = "This is a test upload from Case 07."
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(blob_content, overwrite=True)

        # ✅ FIXED: Key changed from "status" → "message"
        return app.response_class(
            response='{"message": "File uploaded successfully"}',
            status=200,
            mimetype='application/json'
        )

    except Exception as e:
        print("Upload error:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
