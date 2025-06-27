import logging  # Import the logging module
from fastapi import HTTPException, status
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from model import Course, CourseTable, CourseSelection
from schemas.course_selection import CourseSelectionCreate, CourseSelectionUpdate


# Get a logger for this module
logger = logging.getLogger(__name__)


class CourseSelectionService:
    def add_selection(
        self,
        db: Session,
        course_table: CourseTable,
        payload: CourseSelectionCreate,
    ) -> CourseSelection:
        logger.info(
            f"Attempting to add course {payload.course_id} to course table {course_table.id}."
        )

        course_to_add = db.exec(
            select(Course).where(Course.id == payload.course_id)
        ).first()
        if not course_to_add:
            logger.warning(
                f"Failed to add selection - Course {payload.course_id} not found."
            )
            raise HTTPException(status_code=404, detail="Specified course not found.")

        if course_to_add.academic_year_semester != course_table.academic_year_semester:
            logger.warning(
                f"Failed to add selection - Semester mismatch. "
                f"Course {course_to_add.id} is '{course_to_add.academic_year_semester}' "
                f"but table {course_table.id} is '{course_table.academic_year_semester}'."
            )
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Course '{course_to_add.name}' ({course_to_add.academic_year_semester}) "
                    f"semester does not match course table '{course_table.name}' "
                    f"({course_table.academic_year_semester}) semester. Cannot add."
                ),
            )

        existing_in_current_table = db.exec(
            select(CourseSelection).where(
                CourseSelection.course_table_id == course_table.id,
                CourseSelection.course_id == payload.course_id,
            )
        ).first()
        if existing_in_current_table:
            logger.warning(
                f"Failed to add selection - Course {payload.course_id} already exists in table {course_table.id}."
            )
            raise HTTPException(
                status_code=400, detail="Course already exists in this course table."
            )

        selection = CourseSelection(
            course_table_id=course_table.id,
            course_id=payload.course_id,
            note=payload.note,
        )
        try:
            db.add(selection)
            db.commit()
            db.refresh(selection)
            logger.info(
                f"Course selection {selection.id} added successfully to table {course_table.id} for course {course_to_add.id}."
            )
            return selection
        except Exception as e:
            db.rollback()
            logger.error(
                f"Unexpected error adding course {payload.course_id} to table {course_table.id}: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to add course selection. Please try again later.",
            )

    def get_selections(
        self, db: Session, course_table: CourseTable
    ) -> list[CourseSelection]:
        logger.info(f"Retrieving all selections for course table {course_table.id}.")
        try:
            selections = db.exec(
                select(CourseSelection)
                .where(CourseSelection.course_table_id == course_table.id)
                .options(selectinload(CourseSelection.course))
            ).all()
            logger.info(
                f"Found {len(selections)} selections for course table {course_table.id}."
            )
            return selections
        except Exception as e:
            logger.error(
                f"Unexpected error retrieving selections for course table {course_table.id}: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve course selections. Please try again later.",
            )

    def remove_selection(self, db: Session, selection: CourseSelection):
        logger.info(
            f"Attempting to remove course selection {selection.id} from table {selection.course_table_id}."
        )
        try:
            db.delete(selection)
            db.commit()
            logger.info(f"Course selection {selection.id} successfully removed.")
        except Exception as e:
            db.rollback()
            logger.error(
                f"Unexpected error removing course selection {selection.id}: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to delete selection due to an internal error.",
            )

    def update_selection(
        self,
        db: Session,
        selection: CourseSelection,
        payload: CourseSelectionUpdate,
    ) -> CourseSelection:
        logger.info(
            f"Attempting to update course selection {selection.id} in table {selection.course_table_id}."
        )

        if payload.note is not None:
            old_note = selection.note
            selection.note = payload.note
            logger.debug(
                f"Updating note for selection {selection.id} from '{old_note}' to '{selection.note}'."
            )
        else:
            logger.debug(f"No note update for selection {selection.id}.")

        try:
            db.add(selection)
            db.commit()
            db.refresh(selection)
            logger.info(f"Course selection {selection.id} updated successfully.")
            return selection
        except Exception as e:
            db.rollback()
            logger.error(
                f"Unexpected error updating course selection {selection.id}: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to update course selection. Please try again later.",
            )
