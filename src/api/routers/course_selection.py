from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import Session
import logging

from api.dependencies import get_owned_course_table, get_owned_course_selection
from core.database import get_db
from schemas.course_selection import (
    CourseSelectionUpdate,
    CourseSelectionCreate,
    CourseSelectionResponse,
)
from services.course_selection_service import CourseSelectionService
from model import CourseTable, CourseSelection

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Courses selection"],
)
service = CourseSelectionService()


@router.post("/{table_id}", response_model=CourseSelectionResponse)
def add_course_selection(
    *,
    db: Session = Depends(get_db),
    course_table: CourseTable = Depends(get_owned_course_table),
    payload: CourseSelectionCreate,
):
    """
    Adds a course selection to a specific course table owned by the current user.
    """
    logger.info(
        f"Attempting to add course selection for course ID {payload.course_id} to course table ID {course_table.id}."
    )
    try:
        selection = service.add_selection(db, course_table, payload)
        logger.info(
            f"Course selection ID {selection.id} added successfully for course table ID {course_table.id}."
        )
        return CourseSelectionResponse.model_validate(selection)
    except HTTPException as e:
        logger.warning(
            f"Failed to add course selection to table {course_table.id}: {e.detail}"
        )
        raise
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while adding course selection to table {course_table.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add course selection. Please try again later.",
        )


@router.get("/{table_id}", response_model=list[CourseSelectionResponse])
def get_selections_for_table(
    *,
    db: Session = Depends(get_db),
    course_table: CourseTable = Depends(get_owned_course_table),
):
    """
    Retrieves all course selections for a specific course table owned by the current user.
    """
    logger.info(
        f"Attempting to retrieve course selections for course table ID {course_table.id}."
    )
    try:
        selections = service.get_selections(db, course_table)
        logger.info(
            f"Successfully retrieved {len(selections)} course selections for course table ID {course_table.id}."
        )
        return [
            CourseSelectionResponse.model_validate(selection)
            for selection in selections
        ]
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while retrieving selections for table {course_table.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve course selections. Please try again later.",
        )


@router.patch("/{selection_id}", response_model=CourseSelectionResponse)
def update_selection(
    *,
    db: Session = Depends(get_db),
    selection: CourseSelection = Depends(get_owned_course_selection),
    payload: CourseSelectionUpdate,
):
    """
    Updates a specific course selection owned by the current user.
    """
    logger.info(f"Attempting to update course selection ID {selection.id}.")
    try:
        updated_selection = service.update_selection(db, selection, payload)
        logger.info(f"Course selection ID {selection.id} updated successfully.")
        return CourseSelectionResponse.model_validate(updated_selection)
    except HTTPException as e:
        logger.warning(f"Failed to update course selection {selection.id}: {e.detail}")
        raise
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while updating course selection {selection.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update course selection. Please try again later.",
        )


@router.delete("/{selection_id}")
def delete_selection(
    *,
    db: Session = Depends(get_db),
    selection: CourseSelection = Depends(get_owned_course_selection),
):
    """
    Deletes a specific course selection owned by the current user.
    """
    logger.info(f"Attempting to delete course selection ID {selection.id}.")
    try:
        service.remove_selection(db, selection)
        logger.info(f"Course selection ID {selection.id} deleted successfully.")
        return {"message": "Deleted successfully"}
    except HTTPException as e:
        logger.warning(f"Failed to delete course selection {selection.id}: {e.detail}")
        raise
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while deleting course selection {selection.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete course selection. Please try again later.",
        )
