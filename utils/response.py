from flask import jsonify
from utils.json_utils import json_safe

def api_response(status, message, data=None):
    response = {
        "status": status,
        "message": message
    }
    if data is not None:
        response["data"] = json_safe(data)

    return jsonify(response), status
