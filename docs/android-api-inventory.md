## Android API Inventory (Vinor Backend)

This document lists all API endpoints built for the Android/mobile client under the `/api` v1 blueprint. Each entry includes method, path, module/lines, usage summary, auth requirement, and whether a client reference is found in this repo.

Notes:
- Source of truth: `app/api_v1/*` and `app/__init__.py` blueprint registration.
- Client references: No Android project exists in this repository; no references were found in web templates/JS for these paths.
- All endpoints below are considered Android-oriented and are candidates for removal per request.

### Legend
- Auth: Yes = JWT Bearer required; No = public
- Client Ref: Found/Not Found (search for path patterns across repo)

---

### Auth and Profile

| Method | Path                       | Module (approx line)         | Summary                      | Auth | Client Ref |
|--------|----------------------------|-------------------------------|------------------------------|------|------------|
| POST   | `/api/auth/request-otp`    | `app/api_v1/dev.py:22`       | Request OTP code             | No   | Not Found  |
| POST   | `/api/auth/verify-otp`     | `app/api_v1/dev.py:38`       | Verify OTP, issue JWT        | No   | Not Found  |
| GET    | `/api/me`                  | `app/api_v1/dev.py:57`       | Current user profile         | Yes  | Not Found  |

---

### Ads

| Method | Path                           | Module (approx line)          | Summary                                 | Auth | Client Ref |
|--------|--------------------------------|--------------------------------|-----------------------------------------|------|------------|
| GET    | `/api/ads`                     | `app/api_v1/ads.py:42`        | List ads (filters, pagination)          | No   | Not Found  |
| GET    | `/api/ads/<int:id>`            | `app/api_v1/ads.py:94`        | Get ad by id                            | No   | Not Found  |
| POST   | `/api/ads`                     | `app/api_v1/ads.py:102`       | Create new ad                           | Yes  | Not Found  |
| PUT    | `/api/ads/<int:id>`            | `app/api_v1/ads.py:124`       | Update ad (owner only)                  | Yes  | Not Found  |
| DELETE | `/api/ads/<int:id>`            | `app/api_v1/ads.py:141`       | Delete ad (owner only)                  | Yes  | Not Found  |
| POST   | `/api/ads/<int:id>/images`     | `app/api_v1/ads.py:152`       | Upload images for an ad                 | Yes  | Not Found  |

---

### Favorites

| Method | Path                                 | Module (approx line)          | Summary                        | Auth | Client Ref |
|--------|--------------------------------------|--------------------------------|--------------------------------|------|------------|
| GET    | `/api/favorites`                     | `app/api_v1/favorites.py:11`  | List current user's favorites  | Yes  | Not Found  |
| POST   | `/api/favorites/<int:ad_id>`         | `app/api_v1/favorites.py:19`  | Add favorite by ad id          | Yes  | Not Found  |
| DELETE | `/api/favorites/<int:ad_id>`         | `app/api_v1/favorites.py:34`  | Remove favorite by ad id       | Yes  | Not Found  |

---

### Consultation/Contact

| Method | Path                   | Module (approx line)               | Summary                          | Auth | Client Ref |
|--------|------------------------|-------------------------------------|----------------------------------|------|------------|
| POST   | `/api/consultations`  | `app/api_v1/consultations.py:11`   | Create consultation/contact      | No   | Not Found  |

---

### Docs

| Method | Path                   | Module (approx line)          | Summary                          | Auth | Client Ref |
|--------|------------------------|-------------------------------|----------------------------------|------|------------|
| GET    | `/api/openapi.json`    | `app/api_v1/openapi.py:8`     | OpenAPI spec                     | No   | Not Found  |
| GET    | `/api/docs`            | `app/api_v1/openapi.py:44`    | Swagger UI                       | No   | Not Found  |

---

### Development Utilities

| Method | Path             | Module (approx line)      | Summary                           | Auth | Client Ref |
|--------|------------------|---------------------------|-----------------------------------|------|------------|
| POST   | `/api/dev/seed`  | `app/api_v1/dev.py:11`    | Seed sample data (non-production) | No   | Not Found  |

---

### Determination of Android-specific vs. Web-shared

- The entire `app/api_v1` blueprint (`url_prefix="/api"`) was introduced for the mobile client and is not referenced by server-rendered web routes/templates in this repository. Searches across `.py`, `.html`, `.js` found no usage of these `/api/*` endpoints by the web UI.
- Other legacy API blueprints under `app/api/*` (push, uploads, express, sms) appear web-oriented or cross-cutting and are not removed in this step.

### Recommendation for Removal (per request)
- Remove blueprint registration of `api_v1_bp` in `app/__init__.py`.
- Delete the `app/api_v1/` package and its modules (`auth.py`, `ads.py`, `favorites.py`, `consultations.py`, `openapi.py`, `dev.py`, `models.py`, `utils.py`, `__init__.py`).
- No new endpoints added; no refactors beyond deletion.


