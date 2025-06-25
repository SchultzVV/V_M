# from flask import Blueprint, Response, jsonify
# from minio.error import S3Error
# from services.minio_client import minio_client

# media_bp = Blueprint("media", __name__)

# @media_bp.route("/imagens/<bucket>/<filename>")
# def serve_from_minio(bucket, filename):
#     try:
#         response = minio_client.get_object(bucket, filename)
#         return Response(response.stream(32*1024), content_type="image/png")
#     except S3Error:
#         return jsonify({"error": f"Imagem não encontrada: /{bucket}/{filename}"}), 400

from flask import Blueprint, request, redirect, abort, send_file    
from minio import Minio
from minio.error import S3Error
from datetime import timedelta
import os
import io

media_bp = Blueprint("media_bp", __name__)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "amazon")
ACCESS_TOKEN = os.getenv("MEDIA_TOKEN", "secreto123")

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

@media_bp.route("/media/<path:filename>")
def serve_image(filename):
    token = request.args.get("token")
    if token != "secreto123":
        return abort(403)

    bucket = "amazon"
    try:
        obj = minio_client.get_object(bucket, filename)
        return send_file(io.BytesIO(obj.read()), download_name=filename, mimetype="image/png")
    except S3Error:
        return abort(404)
    
# @media_bp.route("/media/<path:filename>")
# def serve_image(filename):
#     token = request.args.get("token")
#     if token != ACCESS_TOKEN:
#         return abort(403, "Acesso negado")

#     try:
#         presigned_url = minio_client.presigned_get_object(
#             MINIO_BUCKET, filename, expires=timedelta(minutes=5)
#         )
#         return redirect(presigned_url)
#     except Exception as e:
#         return abort(404, f"Erro ao buscar imagem: {str(e)}")
