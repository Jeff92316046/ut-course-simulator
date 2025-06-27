from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlmodel import Session
import logging

from api.dependencies import get_current_user, get_owned_course_table
from core.database import get_db
from schemas.course_table import (
    CourseTableCreate,
    CourseTableResponse,
    CourseTableUpdate,
)

from services.course_table_service import CourseTableService
from model import CourseTable, User

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Courses table"],
)
service = CourseTableService()


@router.post("/", response_model=CourseTableResponse)
def create_course_table(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    payload: CourseTableCreate,
):
    """Creates a new course table for the current user."""
    logger.info(
        f"Attempting to create course table for user ID {current_user.id} with name '{payload.name}'."
    )
    try:
        course_table = CourseTableResponse.model_validate(
            service.create_course_table(db, current_user.id, payload)
        )
        logger.info(
            f"Course table ID {course_table.id} created successfully for user ID {current_user.id}."
        )
        return course_table
    except HTTPException as e:
        logger.warning(
            f"Failed to create course table for user {current_user.id}: {e.detail}"
        )
        raise
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while creating course table for user {current_user.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create course table. Please try again later.",
        )


@router.get("/", response_model=list[CourseTableResponse])
def get_user_course_tables(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    academic_year_semester: str | None = Query(None),
):
    """Retrieves all course tables for the current user, with optional semester filter."""
    logger.info(
        f"Attempting to retrieve course tables for user ID {current_user.id} (filter by semester: {academic_year_semester or 'None'})."
    )
    try:
        course_tables = service.get_all_course_tables_by_user(
            db, current_user.id, academic_year_semester
        )
        logger.info(
            f"Successfully retrieved {len(course_tables)} course tables for user ID {current_user.id}."
        )
        return [
            CourseTableResponse.model_validate(course_table)
            for course_table in course_tables
        ]
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while retrieving course tables for user {current_user.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve course tables. Please try again later.",
        )


@router.get("/{table_id}", response_model=CourseTableResponse)
def get_course_table(
    *,
    course_table: CourseTable = Depends(get_owned_course_table),
):
    """Retrieves details for a specific course table by ID."""
    logger.info(
        f"Attempting to retrieve details for course table ID {course_table.id}."
    )
    logger.info(
        f"Successfully retrieved course table ID {course_table.id} for user {course_table.user_id}."
    )
    return CourseTableResponse.model_validate(course_table)


@router.patch("/{table_id}", response_model=CourseTableResponse)
def update_course_table(
    *,
    db: Session = Depends(get_db),
    course_table: CourseTable = Depends(get_owned_course_table),
    payload: CourseTableUpdate,
):
    """Updates an existing course table by ID."""
    logger.info(
        f"Attempting to update course table ID {course_table.id} for user {course_table.user_id}."
    )
    try:
        updated_course_table = service.update_course_table(db, course_table, payload)
        logger.info(f"Course table ID {updated_course_table.id} updated successfully.")
        return CourseTableResponse.model_validate(updated_course_table)
    except HTTPException as e:
        logger.warning(f"Failed to update course table {course_table.id}: {e.detail}")
        raise
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while updating course table {course_table.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update course table. Please try again later.",
        )


@router.delete("/{table_id}")
def delete_course_table(
    *,
    db: Session = Depends(get_db),
    course_table: CourseTable = Depends(get_owned_course_table),
):
    """Deletes a specific course table by ID."""
    logger.info(
        f"Attempting to delete course table ID {course_table.id} for user {course_table.user_id}."
    )
    try:
        service.delete_course_table(db, course_table)
        logger.info(f"Course table ID {course_table.id} deleted successfully.")
        return {"message": "Deleted successfully"}
    except HTTPException as e:
        logger.warning(f"Failed to delete course table {course_table.id}: {e.detail}")
        raise
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while deleting course table {course_table.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete course table. Please try again later.",
        )
