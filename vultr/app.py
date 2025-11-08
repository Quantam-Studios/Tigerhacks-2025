from flask import Flask, request, Response, send_file, jsonify
from pathlib import Path

app = Flask(__name__)

COG_PATH = Path("/srv/marsserver/world_cog.tif")


@app.after_request
def add_cors_headers(resp):
    """Allow Cesium or other web clients to access the file."""
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Accept-Ranges"] = "bytes"
    return resp


@app.route("/")
def root():
    """Basic sanity check endpoint."""
    return {"message": "Flask COG API is live", "file": str(COG_PATH.name)}


@app.route("/world_cog.tif")
def serve_cog():
    """Stream the GeoTIFF file with byte-range (partial) support."""
    if not COG_PATH.exists():
        return jsonify({"error": "COG file not found"}), 404

    range_header = request.headers.get("Range")
    size = COG_PATH.stat().st_size

    # If no Range header, just send the entire file
    if not range_header:
        return send_file(COG_PATH, mimetype="image/tiff")

    # Parse Range header, e.g. "bytes=0-1023"
    byte1, byte2 = 0, None
    range_vals = range_header.replace("bytes=", "").split("-")
    if range_vals[0]:
        byte1 = int(range_vals[0])
    if len(range_vals) > 1 and range_vals[1]:
        byte2 = int(range_vals[1])
    byte2 = byte2 or size - 1
    length = byte2 - byte1 + 1

    with open(COG_PATH, "rb") as f:
        f.seek(byte1)
        data = f.read(length)

    resp = Response(data, 206, mimetype="image/tiff", direct_passthrough=True)
    resp.headers.add("Content-Range", f"bytes {byte1}-{byte2}/{size}")
    return resp


@app.route("/metadata")
def metadata():
    """Lightweight metadata route."""
    if not COG_PATH.exists():
        return jsonify({"error": "COG file not found"}), 404

    size_mb = round(COG_PATH.stat().st_size / (1024 * 1024), 2)
    return {
        "filename": COG_PATH.name,
        "size_MB": size_mb,
        "path": str(COG_PATH),
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)