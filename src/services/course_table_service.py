import uuid
import logging

from fastapi import HTTPException
from sqlmodel import Session, select
from model import CourseTable
from schemas.course_table import CourseTableCreate, CourseTableUpdate


logger = logging.getLogger(__name__)


class CourseTableService:
    def create_course_table(
        self, db: Session, user_id: uuid.UUID, payload: CourseTableCreate
    ) -> CourseTable:
        logger.info(
            f"Attempting to create new course table for user ID {user_id} with name '{payload.name}'."
        )
        try:
            table = CourseTable(
                name=payload.name,
                academic_year_semester=payload.academic_year_semester,
                user_id=user_id,
            )
            db.add(table)
            db.commit()
            db.refresh(table)
            logger.info(
                f"Course table '{table.name}' (ID: {table.id}) "
                f"created successfully for user ID {user_id}."
            )
            return table
        except Exception as e:
            db.rollback()
            logger.error(
                "Unexpected error creating course table"
                f"for user ID {user_id} (name: '{payload.name}'): {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to create course table due to an internal error.",
            )

    def get_all_course_tables_by_user(
        self, db: Session, user_id: uuid.UUID, semester: str | None = None
    ) -> list[CourseTable]:
        logger.info(
            f"Retrieving course tables for user ID {user_id} "
            f"(filter by semester: {semester or 'None'})."
        )
        try:
            query = select(CourseTable).where(CourseTable.user_id == user_id)
            if semester:
                query = query.where(CourseTable.academic_year_semester == semester)

            tables = db.exec(query).all()
            logger.info(f"Found {len(tables)} course tables for user ID {user_id}.")
            return tables
        except Exception as e:
            logger.error(
                "Unexpected error retrieving course tables "
                f" for user ID {user_id} (semester: {semester or 'None'}): {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve course tables due to an internal error.",
            )

    def update_course_table(
        self,
        db: Session,
        table: CourseTable,
        payload: CourseTableUpdate,
    ) -> CourseTable:
        logger.info(
            f"Attempting to update course table ID {table.id} for user ID {table.user_id}."
        )

        updated_fields = []
        if payload.name is not None and payload.name != table.name:
            logger.debug(
                f"Updating name for table ID {table.id}: "
                f"From '{table.name}' to '{payload.name}'."
            )
            table.name = payload.name
            updated_fields.append("name")

        if not updated_fields:
            logger.info(
                f"No fields to update for course table ID {table.id}. Returning existing table."
            )
            return table

        try:
            db.add(table)
            db.commit()
            db.refresh(table)
            logger.info(
                f"Course table ID {table.id} "
                f"updated successfully (Fields updated: {', '.join(updated_fields) or 'None'})."
            )
            return table
        except Exception as e:
            db.rollback()
            logger.error(
                f"Unexpected error updating course table ID {table.id} for user ID {table.user_id}: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to update course table due to an internal error.",
            )

    def delete_course_table(self, db: Session, table: CourseTable):
        logger.info(
            f"Attempting to delete course table ID {table.id} for user ID {table.user_id}."
        )
        try:
            db.delete(table)
            db.commit()
            logger.info(f"Course table ID {table.id} successfully deleted.")
        except Exception as e:
            db.rollback()
            logger.error(
                f"Unexpected error deleting course table ID {table.id} for user ID {table.user_id}: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to delete course table due to an internal error.",
            )
