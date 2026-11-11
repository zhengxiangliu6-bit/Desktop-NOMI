from fastapi import APIRouter, Request

from app.settings.models import ConnectionTest, PairRequest, ProfileUpdate

router = APIRouter(prefix="/api/v0/settings")


@router.post("/pair")
async def pair(body: PairRequest, request: Request):
    return {
        "token": request.app.state.local_admin.pair(body.code.get_secret_value()),
        "expires_in": 1800,
    }


@router.post("/read")
async def read_settings(request: Request):
    return request.app.state.local_admin.public()


@router.put("")
async def update_settings(body: ProfileUpdate, request: Request):
    result = request.app.state.local_admin.update(body, request.app.state.conversation)
    return result


@router.post("/test")
async def test_connection(body: ConnectionTest, request: Request):
    return await request.app.state.local_admin.test_connection(body.revision)
