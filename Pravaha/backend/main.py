from fastapi import FastAPI, Depends, HTTPException, Response, status, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from jose import jwt, JWTError
import uvicorn
import bcrypt
import os
import asyncio
from typing import Dict, Optional
from dotenv import load_dotenv

try:
    load_dotenv()  # Load environment variables
except OSError:
    # macOS: [Errno 89] Operation canceled can occur during uvicorn hot-reload
    pass

# Custom imports
from utils.database import APP_DB_NAME, Database, db
from utils.auth import (
    ALGORITHM,
    ACCESS_TOKEN_COOKIE_NAME,
    SECRET_KEY,
    SESSION_SECRET,
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
)
from routers.chat import router as chat_router
from routers.chat.buyer_chat import router as buyer_chat_router
from routers.admin import router as admin_router
from routers.events.buyer_events import router as buyer_events_router
from routers.events.call_events import router as call_events_router
from routers.events.proposal_events import router as proposal_events_router
from routers.events.email_events import router as email_events_router

desc = """
Pravaha is a revolutionary tool designed to streamline the sales process by gathering customer data and generating tailored sales proposals efficiently.
Combining advanced language models and speech recognition technology, it enables seamless interaction via voice or text inputs, making it ideal for live conversations and phone calls.
The assistant engages users interactively, extracting essential details from documents provided by customers and performing information gap analysis to ensure proposal completeness.
By automating tedious tasks and improving data accuracy, it empowers sales teams to focus on building strong customer relationships and closing deals effectively.
## Overview:
In response to the challenges faced by sales teams in gathering comprehensive customer data and generating tailored sales proposals efficiently, we propose the development of an AI- powered Sales Assistant. This assistant leverages advanced language models (LLMs) and speech recognition technologies to streamline the sales process, enhance customer engagements, and improve the accuracy and effectiveness of sales proposals.
## Key Features:
- **Voice Activation**: The AI Sales Assistant supports both voice and text inputs, enabling seamless interaction during live conversations such as meetings and phone calls. This feature ensures accessibility and ease of use for sales representatives, allowing them to gather information and generate proposals in real-time.
- **Interactive Engagement**: Through intelligent questioning, the AI assistant engages with users to gather relevant customer data necessary for creating tailored sales proposals. By dynamically adapting its queries based on the context of the conversation, the assistant ensures that no critical details are overlooked.
- **Document Analysis**: The AI Sales Assistant possesses the capability to analyze documents provided by customers, such as PDF files, to extract essential information required for drafting sales proposals. This feature eliminates manual data entry tasks and accelerates the proposal generation process by automatically capturing pertinent details.
- **Information Gap Analysis**: To further enhance the accuracy and completeness of sales proposals, the assistant performs information gap analysis. By identifying any missing details or inconsistencies in the gathered data, the assistant prompts users to provide additional information necessary for completing the proposal accurately.
"""


openapi_tags = [
    {
        "name": "general",
        "description": """
# General API Endpoints

These endpoints cover user authentication, user registration, and basic interactions. Here's an overview of each endpoint's functionality:

## `POST /token`
This endpoint is used for user login. It validates the provided username and password using OAuth2, then returns a Bearer token for further authentication.

- **Request Parameters:** 
  - OAuth2PasswordRequestForm containing:
    - `username` (str): The username for login.
    - `password` (str): The password for login.
- **Response:** A JSON object with an `access_token` and `token_type`.
- **Error Handling:** If the login fails, it raises an HTTP 401 error with a "Bearer" authentication challenge.

## `POST /register`
This endpoint is used to register new users. It creates a new user with a hashed password and stores it in the database.

- **Request Parameters:** 
  - `UserRegister` model containing:
    - `username` (str): The desired username.
    - `email` (EmailStr): The user's email address.
    - `password` (str): The plain text password (will be hashed).
- **Response:** A JSON object indicating successful registration, with the username and email of the new user.
- **Error Handling:** If the username is already taken, it raises an HTTP 400 error.

## `GET /me`
This endpoint retrieves the current logged-in user's details based on the provided Bearer token.

- **Authorization:** Requires a Bearer token (provided via `oauth2_scheme`).
- **Response:** A JSON object with the user's details.
- **Error Handling:** If the token is invalid or the user cannot be found, it raises an HTTP 401 error.

## `GET /secure-route`
A secure endpoint that requires authentication. It returns a personalized greeting for the logged-in user.

- **Authorization:** Requires a Bearer token for authentication.
- **Response:** A JSON object with a personalized greeting, referencing the current user's username.

## `GET /`
A simple root endpoint that returns a basic greeting message.

- **Response:** A JSON object with a `"message"` key and the value `"Hello World"`.

    """,
    },
    {
        "name": "admin",
        "description": """
# Admin API Endpoints

This API is intended for administrative tasks related to managing documents, generating proposals, sending emails, and other operations. The following endpoints are available:

## `GET /admin/`
A simple health check for the `admin` router. It returns a basic message to indicate that the router is operational.

- **Response:** A JSON object with a `"message"` key and the value `"Admin Endpoint"`.

## `GET /admin/analytics`
Returns analytics data for administrative purposes. Requires admin-level authorization.

- **Authorization:** Requires admin privileges (`is_admin` dependency).
- **Response:** A JSON object containing analytics data.

## `POST /admin/upload_pdf`
Uploads a PDF file to the server. The PDF is processed and stored for later use. Requires admin authorization.

- **Authorization:** Requires admin privileges.
- **Request Parameters:** 
  - `pdf_file` (UploadFile): The PDF file to upload.
- **Response:** A JSON object with details of the upload status.

## `POST /admin/update_selected_docs`
Updates the list of selected documents. This endpoint checks whether the specified files exist before updating the list.

- **Authorization:** Requires admin privileges.
- **Request Parameters:** 
  - `filenames` (List[str]): List of document filenames to update.
- **Response:** A simple success message if the operation was successful.

## `GET /admin/ingest`
Ingests PDFs into the system for further processing. Requires admin authorization.

- **Authorization:** Requires admin privileges.
- **Response:** A JSON object with a `"message"` key and a status update.

## `GET /admin/generate_proposal`
Generates a proposal from previously uploaded documents. Requires admin authorization.

- **Authorization:** Requires admin privileges.
- **Response:** A JSON object with the generated proposal details.

## `GET /admin/get_selected_docs`
Returns the list of selected documents currently stored in the system. Requires admin authorization.

- **Authorization:** Requires admin privileges.
- **Response:** A JSON object with the list of selected document names.

## `GET /admin/get_all_docs`
Returns a list of all available documents in the system. Requires admin authorization.

- **Authorization:** Requires admin privileges.
- **Response:** A JSON object with the list of all document names.

## `POST /admin/send_bulk_email`
Sends bulk emails to a list of recipients using a specified template. Requires admin authorization.

- **Authorization:** Requires admin privileges.
- **Request Parameters:** 
  - `template` (str): The email template to use.
  - `email_list` (List[str]): List of email addresses to send to.
- **Response:** A JSON object with the result of the email operation.

## `POST /admin/call`
Initiates a call to a specified mobile number with a given template. Requires admin authorization.

- **Authorization:** Requires admin privileges.
- **Request Parameters:** 
  - `CallRequest` model containing:
    - `mobile` (str): The mobile number to call.
    - `template` (str): The template for the call.
- **Response:** A JSON object with the result of the call.

## `GET /admin/get_last_summary`
Returns the latest summary generated by the system. Requires admin authorization.

- **Authorization:** Requires admin privileges.
- **Response:** A JSON object with the most recent summary.

## `GET /admin/get_html_from_file`
Retrieves HTML content from a specified file. Requires admin authorization.

- **Authorization:** Requires admin privileges.
- **Request Parameters:** 
  - `file_name` (str): The name of the file to retrieve.
- **Response:** The content of the specified file, returned as HTML. Raises a 404 error if the file is not found.


    """,
    },
    {
        "name": "chat",
        "description": """

# Chat API Endpoints

This API allows for interaction with a chatbot and manages chat sessions. The following endpoints are available:

## `GET /chat/`
This endpoint is a simple health check for the `chat` router. It returns a "Hello World" message to indicate that the router is operational.

- **Response:** A JSON object with a `"message"` key and the value `"Hello World"`.

## `POST /chat/response`
This endpoint takes a text query and returns a response from the chatbot. The chatbot instance is tied to the session, allowing for context-aware interactions.

- **Request Parameters:**
  - `query` (str): The text query to send to the chatbot.
- **Response:** A JSON object with a `"response"` key containing the chatbot's response to the query.

## `GET /chat/close_session`
This endpoint closes the current chat session, removing the associated chatbot instance. It is useful for cleaning up session-related data when no longer needed.

- **Response:** A JSON object with a `"message"` key and the value `"Session closed"`.

""",
    },
]
app = FastAPI(
    title="Pravaha API",
    description=desc,
    openapi_tags=openapi_tags,
    version="1.0.0",
    contact={
        "name": "Team ARKA",
        "url": "https://github.com/junaidjmomin/Pravaha",
    },
)

app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,https://pravaha.vercel.app",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router)
app.include_router(buyer_chat_router)   # public proposal + buyer chat (no auth)
app.include_router(admin_router)

# Zapier + MCP event layer (public event endpoints — no auth needed for buyer events)
app.include_router(buyer_events_router)
app.include_router(call_events_router)
app.include_router(proposal_events_router)
app.include_router(email_events_router)


@app.on_event("startup")
async def _startup_zapier_mcp():
    """Register Zapier webhook listeners and MCP orchestrator at startup."""
    from utils.zapier_webhooks import register_zapier_listeners
    from utils.mcp_orchestrator import register_orchestrator
    register_zapier_listeners()
    register_orchestrator()

    # Schedule stale proposal detection every 6 hours using APScheduler
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from utils.stale_detector import detect_stale_proposals
        _scheduler = AsyncIOScheduler()
        _scheduler.add_job(detect_stale_proposals, "interval", hours=6, id="stale_detector")
        _scheduler.start()
    except Exception:
        pass  # APScheduler optional — stale detection can also be triggered manually


def _auth_cookie_settings(request: Request) -> dict:
    secure = request.url.scheme == "https"
    return {
        "httponly": True,
        "secure": secure,
        "samesite": "none" if secure else "lax",
        "max_age": 60 * 60 * 6,
        "path": "/",
    }


@app.post("/token", tags=["general"])
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    Obtain a Bearer token for login.

    Use the OAuth2 authentication scheme to validate the username and password.
    Returns an access token to be used for further authentication.
    """
    user = authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=360)
    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]}, expires_delta=access_token_expires
    )
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        **_auth_cookie_settings(request),
    )

    return {"access_token": access_token, "token_type": "bearer", "role": user["role"]}


@app.post("/logout", tags=["general"])
async def logout(request: Request, response: Response):
    cookie_settings = _auth_cookie_settings(request)
    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        path=cookie_settings["path"],
        samesite=cookie_settings["samesite"],
        secure=cookie_settings["secure"],
    )
    return {"message": "Logged out"}


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str  # Plain text password (will be hashed before storing)


@app.post("/register", status_code=status.HTTP_201_CREATED, tags=["general"])
async def register_user(user: UserRegister):
    """
    Register a new user.

    Expects a `UserRegister` model containing a username, email, and password.
    The password is hashed before storing in the database. If the username is
    already taken, an HTTP 400 error is raised.
    """
    # Check if user already exists
    existing_user = db.get_user_by_username(user.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Hash the password
    hashed_password = get_password_hash(user.password)

    # Store the new user in the database
    try:
        # Self-serve registration intentionally provisions the base assistant role only.
        db.create_user(user.username, user.email, hashed_password, role="user")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return {
        "message": "User registered successfully",
        "username": user.username,
        "email": user.email,
    }


@app.get("/me",tags=["general"])
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """
    Retrieve the current logged-in user based on the provided token.

    Requires a Bearer token for authentication. If the token is invalid or the user
    cannot be found, an HTTP 401 error is raised.
    """
    return {**current_user, "role": current_user.get("role", "user")}


@app.get("/secure-route", tags=["general"])
async def secure_endpoint(current_user: dict = Depends(read_users_me)):
    """
    A secure endpoint that requires authentication.

    Returns a personalized greeting for the logged-in user.
    """
    return {"message": f"Hello, {current_user['username']}!"}


@app.get("/", tags=["general"])
async def root():
    """
    A simple root endpoint that returns a greeting message.
    """
    return {"message": "Hello World"}

# ─── WebSocket coaching connections (call_id → WebSocket) ────────────────
active_coaching_sessions: Dict[str, WebSocket] = {}
automation_scheduler_task: Optional[asyncio.Task] = None


async def automation_scheduler_loop():
    from utils.automations import ensure_default_automations, run_due_automations_once

    poll_seconds = int(os.getenv("AUTOMATION_POLL_SECONDS", "60"))
    ensure_default_automations()

    while True:
        try:
            run_due_automations_once(triggered_by="scheduler")
        except Exception:
            # Keep the scheduler alive; operational failures are logged in run history.
            pass
        await asyncio.sleep(max(15, poll_seconds))


@app.on_event("startup")
async def startup_background_workers():
    global automation_scheduler_task
    if os.getenv("ENABLE_AUTOMATION_SCHEDULER", "1") == "0":
        return
    if automation_scheduler_task and not automation_scheduler_task.done():
        return
    automation_scheduler_task = asyncio.create_task(automation_scheduler_loop())


@app.on_event("shutdown")
async def shutdown_background_workers():
    global automation_scheduler_task
    if automation_scheduler_task is None:
        return
    automation_scheduler_task.cancel()
    try:
        await automation_scheduler_task
    except asyncio.CancelledError:
        pass
    automation_scheduler_task = None


@app.websocket("/ws/coaching/{call_id}")
async def coaching_websocket(websocket: WebSocket, call_id: str):
    """
    Sales rep connects here when a call starts.
    VAPI webhook pushes coaching tips to this connection in real-time.
    """
    await websocket.accept()
    active_coaching_sessions[call_id] = websocket
    try:
        while True:
            # Keep alive — rep can also send messages here
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_coaching_sessions.pop(call_id, None)


@app.post("/webhook/vapi", tags=["general"])
async def vapi_webhook(request: Request):
    """
    VAPI sends live transcript chunks here.
    We analyze each customer utterance and push coaching tips to the rep's WebSocket.
    """
    import hmac
    import hashlib
    import json as _json
    from utils.coaching import analyze_utterance

    body = await request.body()

    webhook_secret = os.getenv("VAPI_WEBHOOK_SECRET")
    if webhook_secret:
        signature = request.headers.get("x-vapi-signature", "")
        expected = hmac.new(
            webhook_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = _json.loads(body)
    except Exception:
        return {"status": "ignored"}

    call_id = payload.get("call_id", "")
    transcript_chunk = payload.get("transcript", "")
    speaker = payload.get("role", payload.get("speaker", ""))
    app_db = Database(APP_DB_NAME)

    if call_id and transcript_chunk:
        transcript_event = {
            "event": "transcript",
            "transcript": {
                "call_id": call_id,
                "role": speaker or "unknown",
                "text": transcript_chunk,
                "timestamp": datetime.utcnow().isoformat(),
            },
        }
        try:
            app_db.append_live_transcript_chunk(call_id, speaker or "unknown", transcript_chunk)
        except Exception:
            pass

        if call_id in active_coaching_sessions:
            ws = active_coaching_sessions[call_id]
            try:
                await ws.send_text(_json.dumps(transcript_event))
            except Exception:
                active_coaching_sessions.pop(call_id, None)

    # Only analyze when the customer (not assistant) speaks
    if (speaker or "").strip().lower() not in ("customer", "user", "human", "client"):
        return {"status": "ignored"}

    tip = analyze_utterance(transcript_chunk)

    if tip.get("type") != "none":
        # Persist tip to MongoDB
        import uuid as _uuid
        from datetime import datetime as _dt
        tip_doc = {
            "tip_id": str(_uuid.uuid4()),
            "call_id": call_id,
            "type": tip.get("type"),
            "subtype": tip.get("subtype"),
            "detected": tip.get("detected"),
            "suggested_response": tip.get("suggested_response"),
            "relevant_document": tip.get("relevant_document"),
            "urgency": tip.get("urgency"),
            "utterance": transcript_chunk,
            "timestamp": _dt.utcnow(),
            "feedback": None,
        }
        try:
            app_db.save_coaching_tip(tip_doc)
        except Exception as e:
            print(f"[Coaching] Failed to save tip: {e}")

        # Push to WebSocket if rep is connected
        if call_id in active_coaching_sessions:
            ws = active_coaching_sessions[call_id]
            try:
                await ws.send_text(_json.dumps({"event": "coaching_tip", "tip": tip}))
            except Exception:
                active_coaching_sessions.pop(call_id, None)

    return {"status": "ok", "tip_type": tip.get("type")}


# Run the server
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
