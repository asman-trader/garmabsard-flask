from __future__ import annotations

from flask import Response

from . import api_v1_bp


@api_v1_bp.get("/openapi.json")
def openapi_json():
    # Minimal OpenAPI spec covering Phase 1
    spec = {
        "openapi": "3.0.3",
        "info": {"title": "Vinor API", "version": "1.0.0"},
        "paths": {
            "/api/auth/request-otp": {"post": {"summary": "Request OTP", "responses": {"200": {"description": "OK"}}}},
            "/api/auth/verify-otp": {"post": {"summary": "Verify OTP", "responses": {"200": {"description": "OK"}}}},
            "/api/me": {"get": {"summary": "Get current user", "responses": {"200": {"description": "OK"}}}},
            "/api/ads": {"get": {"summary": "List ads", "responses": {"200": {"description": "OK"}}}, "post": {"summary": "Create ad", "responses": {"201": {"description": "Created"}}}},
            "/api/ads/{id}": {
                "get": {"summary": "Get ad", "responses": {"200": {"description": "OK"}, "404": {"description": "Not Found"}}},
                "put": {"summary": "Update ad", "responses": {"200": {"description": "OK"}}},
                "delete": {"summary": "Delete ad", "responses": {"200": {"description": "OK"}}},
            },
            "/api/ads/{id}/images": {"post": {"summary": "Upload ad images", "responses": {"200": {"description": "OK"}}}},
            "/api/favorites": {"get": {"summary": "List favorites", "responses": {"200": {"description": "OK"}}}},
            "/api/favorites/{ad_id}": {
                "post": {"summary": "Add favorite", "responses": {"201": {"description": "Created"}}},
                "delete": {"summary": "Remove favorite", "responses": {"200": {"description": "OK"}}},
            },
            "/api/consultations": {"post": {"summary": "Create consultation", "responses": {"200": {"description": "OK"}}}},
        },
        "components": {"securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}}},
        "security": [{"bearerAuth": []}],
    }
    return Response(response=json_dump_bytes(spec), status=200, mimetype="application/json")


def json_dump_bytes(obj) -> bytes:
    import json

    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


@api_v1_bp.get("/docs")
def swagger_ui():
    # Simple Swagger UI via CDN
    html = """
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Vinor API Docs</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui.css" />
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui-bundle.js" crossorigin></script>
    <script>
      window.ui = SwaggerUIBundle({
        url: '/api/openapi.json',
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
      });
    </script>
  </body>
</html>"""
    return Response(html, status=200, mimetype="text/html; charset=utf-8")


