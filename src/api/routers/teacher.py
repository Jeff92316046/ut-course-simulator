from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import select, Session
import uuid
from typing import List

from schemas.teacher import CourseScheduleResponse
from services.teacher_service import TeacherService
from core.database import get_db
from api.dependencies import get_current_user
from schemas.course import (
    Teacher as TeacherResponse,
    Course as CourseResponse,
)
from model import User


service = TeacherService()
router = APIRouter(
    tags=["Teachers"],
)


@router.get("/search", response_model=List[TeacherResponse])
def search_teachers(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    name: str = Query(
        ..., min_length=1, description="Partial or full teacher name for fuzzy search"
    ),
):
    teachers = service.search_teachers_by_name(db, name_query=name)

    response_data = [TeacherResponse.model_validate(teacher) for teacher in teachers]

    return response_data


@router.get("/{teacher_id}/courses", response_model=List[CourseResponse])
def get_all_courses_taught_by_teacher(
    *,
    teacher_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    academic_year_semester: str | None = Query(
        None, description="學年學期, e.g., '113-1'"
    ),
):
    courses = service.get_teacher_all_courses(
        db=db,
        teacher_id=teacher_id,
        academic_year_semester=academic_year_semester,
    )

    response_data = [CourseResponse.model_validate(course) for course in courses]

    return response_data


@router.get("/{teacher_id}/schedule_slots", response_model=List[CourseScheduleResponse])
def get_teacher_all_schedule_slots(
    *,
    teacher_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    academic_year_semester: str | None = Query(
        None, description="學年學期, e.g., '113-1'"
    ),
):
    schedule_slots = service.get_teacher_schedule_slots(
        db=db,
        teacher_id=teacher_id,
        academic_year_semester=academic_year_semester,
    )

    response_data = [
        CourseScheduleResponse.model_validate(slot) for slot in schedule_slots
    ]

    return response_data
