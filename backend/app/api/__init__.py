from fastapi import APIRouter

from app.api import appointments, auth, calendar, chat, consultation, doctors, leave, slots

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(doctors.router)
api_router.include_router(slots.router)
api_router.include_router(appointments.router)
api_router.include_router(consultation.router)
api_router.include_router(leave.router)
api_router.include_router(chat.router)
api_router.include_router(calendar.router)
