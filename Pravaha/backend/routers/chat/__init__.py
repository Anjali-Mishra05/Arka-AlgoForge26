import uuid
from datetime import datetime

from fastapi import Depends, HTTPException, Request, APIRouter
from pydantic import BaseModel
from utils.chatbot import ChatBot
from utils.database import Database
from utils.auth import ACCESS_TOKEN_COOKIE_NAME, SECRET_KEY, ALGORITHM, get_current_user
from jose import jwt, JWTError

from .response import respond

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    responses={404: {"description": "Not found"}},
)

chatbots = {}

def get_role_from_request(request: Request) -> str:
    """Extract user role from Bearer token in Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME, "")

    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload.get("role", "user")
        except JWTError:
            pass
    return "user"

def get_chatbot(request: Request, current_user: dict = None):
    session_id = request.session.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        request.session["session_id"] = session_id
    role = "user"  # Default role
    if current_user:
        role = current_user.get("role") or get_role_from_request(request)
    owner = "anonymous"  # Default owner
    if current_user:
        owner = current_user.get("email") or current_user.get("username") or "unknown"
    key = f"{session_id}:{owner}:{role}"
    if key not in chatbots:
        chatbots[key] = ChatBot(role=role)
    return chatbots[key]


def _require_rep_or_admin(current_user: dict) -> str:
    role = current_user.get("role") or "user"
    if role not in {"team", "admin"}:
        raise HTTPException(status_code=403, detail="Next-best action is only available for team and admin roles.")
    return role


class ChatNextBestActionTrackRequest(BaseModel):
    event: str
    notes: str = ""
    metadata: dict = {}


@router.get("/")
async def check():
    return {"message": "Hello World"}

@router.post("/response")
async def response(query: str, request: Request, current_user: dict = Depends(get_current_user)):
    db = Database("pravaha_app")
    await db.update_endpoint("/chat/response")
    role = current_user.get("role") or "user"
    query = query.strip()
    
    # Get chatbot for this user and role
    chatbot = get_chatbot(request, current_user)
    
    # Call respond
    ai_response = await respond(chatbot, query)
    
    return {"response": ai_response, "role": role}


# Dedicated coaching endpoint — always uses "team" role for tactical objection handling
_coach_bots = {}


@router.post("/coach")
async def coach_response(query: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Sales Coach endpoint — forces 'team' role for tactical coaching responses."""
    db = Database("pravaha_app")
    await db.update_endpoint("/chat/coach")
    session_id = request.session.get("session_id") or str(uuid.uuid4())
    key = f"{session_id}:{current_user.get('email')}:team"
    if key not in _coach_bots:
        _coach_bots[key] = ChatBot(role="team")
    bot = _coach_bots[key]
    query = query.strip()
    ai_response, sources = await respond(
        bot,
        query,
        return_sources=True,
    )
    return {"response": ai_response, "role": "team", "sources": sources}


@router.get("/next_best_action")
async def chat_next_best_action(
    refresh: bool = False,
    current_user: dict = Depends(get_current_user),
):
    role = _require_rep_or_admin(current_user)
    user_scope = current_user.get("email") or current_user.get("username")
    if not user_scope:
        raise HTTPException(status_code=400, detail="Missing user scope")

    if role == "admin":
        from routers.admin.intelligence import _build_next_best_action

        return _build_next_best_action(refresh=refresh)

    from routers.admin.intelligence import _build_next_best_action

    return _build_next_best_action(user_scope, refresh=refresh)


@router.post("/next_best_action/track")
async def chat_track_next_best_action(
    body: ChatNextBestActionTrackRequest,
    current_user: dict = Depends(get_current_user),
):
    role = _require_rep_or_admin(current_user)
    user_scope = current_user.get("email") or current_user.get("username")
    if not user_scope:
        raise HTTPException(status_code=400, detail="Missing user scope")

    from routers.admin.intelligence import track_next_best_action

    tracked = track_next_best_action(None if role == "admin" else user_scope, body.event, body.notes, body.metadata)
    return tracked or {"status": "missing"}


@router.get("/close_session")
async def close_session(request: Request, current_user: dict = Depends(get_current_user)):
    current_chatbot = get_chatbot(request, current_user)
    session_id = request.session.get("session_id")
    role = current_user.get("role") or get_role_from_request(request)
    owner = current_user.get("email") or current_user.get("username") or "unknown"
    key = f"{session_id}:{owner}:{role}"
    
    if key in chatbots:
        del chatbots[key]

    if current_chatbot is not None:
        await current_chatbot.append_session(session_id)

    return {"message": "Session closed"}