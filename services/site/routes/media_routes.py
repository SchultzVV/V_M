from flask import Blueprint, Response, jsonify
from minio.error import S3Error
from services.minio_client import minio_client

media_bp = Blueprint("media", __name__)

@media_bp.route("/imagens/<bucket>/<filename>")
def serve_from_minio(bucket, filename):
    try:
        response = minio_client.get_object(bucket, filename)
        return Response(response.stream(32*1024), content_type="image/png")
    except S3Error:
        return jsonify({"error": f"Imagem não encontrada: /{bucket}/{filename}"}), 400
