# SkySolve Next API Documentation

This document describes the REST API endpoints provided by the SkySolve Next backend. All endpoints are served from the FastAPI app (default port: 5001).

---

## Endpoints

### 1. GET `/status`
Returns current system status.

**Request:**
```
GET /status
```

**Response:**
```json
{
  "mode": "solve",
  "fps": 0.0,
  "last_conf": null
}
```

---

### 2. POST `/mode`
Sets the system mode.

**Request:**
```
POST /mode
Content-Type: application/json

{
  "mode": "solve"
}
```

**Response:**
```json
{
  "mode": "solve",
  "fps": 0.0,
  "last_conf": null
}
```

---

### 3. GET `/`
Returns the main web UI HTML page.

**Request:**
```
GET /
```

**Response:**
HTML content of the UI.

---

### 4. GET `/static/demo.jpg`
Returns the demo image file.

**Request:**
```
GET /static/demo.jpg
```

**Response:**
Binary image data (JPEG).

---

### 5. POST `/solve`
Solves an uploaded image or loads the demo image if requested.

**Request (demo):**
```
POST /solve?demo=1
```

**Response (demo):**
```json
{
  "result": "success",
  "image_url": "/static/demo.jpg",
  "message": "Demo image loaded."
}
```

**Request (upload):**
```
POST /solve
Content-Type: multipart/form-data
(image file in 'image' field)
```

**Response (upload):**
```json
{
  "result": "success",
  "message": "Solve endpoint called."
}
```

---

### 6. POST `/onstep/push`
Pushes the last solved coordinates to OnStep (dummy response).

**Request:**
```
POST /onstep/push
```

**Response:**
```json
{
  "result": "success",
  "message": "OnStep push endpoint called."
}
```

---

### 7. POST `/auto-solve`
Enables or disables auto-solve mode.

**Request:**
```
POST /auto-solve
Content-Type: application/json

{
  "enabled": true
}
```

**Response:**
```json
{
  "result": "success",
  "auto_solve": true
}
```

---

### 8. POST `/auto-push`
Enables or disables auto-push to OnStep.

**Request:**
```
POST /auto-push
Content-Type: application/json

{
  "enabled": true
}
```

**Response:**
```json
{
  "result": "success",
  "auto_push": true
}
```

---

### 9. WebSocket `/events`
Streams system events (demo only).

**Request:**
```
WebSocket /events
```

**Response (on connect):**
```json
{
  "event": "hello",
  "port_web": 5001
}
```

---

## Notes
- All endpoints are subject to change; this document will be updated as APIs evolve.
- For file uploads, use `multipart/form-data` with the image in the `image` field.
- For demo mode, use `POST /solve?demo=1`.
- For questions or contributions, see the main README and implementation plan in `docs/`.
