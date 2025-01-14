from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.friend_requests import FriendRequestIn
from app.schemas.dms import DmsOut, DmMessagesOut
from app.db.database import get_db
from app.core.oauth import get_current_user
from app.models.user import Users
from app.routers.server_websocket.ServerConnectionManager import server_manager
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.dms import check_already_created_dm, create_new_dm, get_all_dms, check_user_in_dm, get_all_dm_information, \
    get_all_dm_messages
from typing import List

router = APIRouter()


@router.post("/dm")
async def create_dm(friend_request: FriendRequestIn, current_user: Users = Depends(get_current_user),
                    db: AsyncSession = Depends(get_db)):
    already_dm = await check_already_created_dm(db=db, current_user_username=current_user.username,
                                                remote_user_username=friend_request.username)
    if already_dm:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="There is already a dm")
    dm = await create_new_dm(db=db, current_user_username=current_user.username,
                             remote_user_username=friend_request.username)
    server_manager.add_valid_server_or_dm(usernames=[dm["sender"], dm["receiver"]], type="dm_ids", id=dm["dm_id"])
    notification = {"chat": "notification", "type": "newdm", "sender": dm["sender"], "receiver": dm["receiver"]}
    await server_manager.broadcast_from_route(sender_username=current_user.username, message=notification, db=db)
    await db.commit()


@router.get("/dms", response_model=List[DmsOut])
async def get_dms(current_user: Users = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    dms = await get_all_dms(db=db, current_user_username=current_user.username)
    return dms


@router.get("/dm/{dm_id}", response_model=DmsOut)
async def get_dm_information(dm_id: int, current_user: Users = Depends(get_current_user),
                             db: AsyncSession = Depends(get_db)):
    in_dm = await check_user_in_dm(db=db, current_user_username=current_user.username, dm_id=dm_id)
    if not in_dm:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a part of this dm")
    dm_information = await get_all_dm_information(db=db, current_user_username=current_user.username, dm_id=dm_id)
    return dm_information


@router.get("/dmmessages/{dm_id}", response_model=List[DmMessagesOut])
async def get_dm_messages(dm_id: int, current_user: Users = Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)):
    in_dm = await check_user_in_dm(db=db, current_user_username=current_user.username, dm_id=dm_id)
    if not in_dm:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a part of this dm")
    dm_messages = await get_all_dm_messages(db=db, dm_id=dm_id)
    return dm_messages
