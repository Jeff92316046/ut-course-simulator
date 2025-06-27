import uuid
import logging

from fastapi import HTTPException, status
from sqlmodel import Session, col, func, select
from sqlalchemy.orm import selectinload
from model import Course, CourseSchedule, CourseTeacher, Teacher


logger = logging.getLogger(__name__)


class TeacherService:
    def get_teacher_all_courses(
        self,
        *,
        db: Session,
        teacher_id: uuid.UUID,
        academic_year_semester: str | None = None,
    ) -> list[Course]:
        logger.info(
            f"Attempting to retrieve all courses for teacher ID {teacher_id} "
            f"(semester: {academic_year_semester or 'All'})."
        )

        try:
            query = select(Course)
            query = (
                query.join(CourseTeacher, CourseTeacher.course_id == Course.id)
                .join(Teacher, Teacher.id == CourseTeacher.teacher_id)
                .where(Teacher.id == teacher_id)
            )

            query = query.options(
                selectinload(Course.teachers), selectinload(Course.schedule_slots)
            )

            if academic_year_semester:
                query = query.where(
                    Course.academic_year_semester == academic_year_semester
                )
                logger.debug(
                    f"Applied academic year semester filter: {academic_year_semester}."
                )

            query = query.distinct()
            logger.debug("Applied DISTINCT clause to course query.")

            courses = db.exec(query).all()
            logger.info(
                f"Successfully retrieved {len(courses)} courses for teacher ID {teacher_id}."
            )
            return courses
        except Exception as e:
            logger.error(
                f"Unexpected error retrieving courses for teacher ID {teacher_id} "
                f"(semester: {academic_year_semester or 'All'}): {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve teacher's courses due to an internal error.",
            )

    def get_teacher_schedule_slots(
        self,
        *,
        db: Session,
        teacher_id: uuid.UUID,
        academic_year_semester: str | None = None,
    ) -> list[CourseSchedule]:
        logger.info(
            f"Attempting to retrieve schedule slots for teacher ID {teacher_id} "
            f"(semester: {academic_year_semester or 'All'})."
        )

        try:
            teacher_exists = db.exec(
                select(Teacher.id).where(Teacher.id == teacher_id)
            ).first()
            if not teacher_exists:
                logger.warning(
                    f"Failed to retrieve schedule slots: Teacher ID {teacher_id} not found."
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Teacher not found",
                )

            query = select(CourseSchedule)
            query = (
                query.join(Course, Course.id == CourseSchedule.course_id)
                .join(CourseTeacher, CourseTeacher.course_id == Course.id)
                .join(Teacher, Teacher.id == CourseTeacher.teacher_id)
                .where(Teacher.id == teacher_id)
            )

            if academic_year_semester:
                query = query.where(
                    Course.academic_year_semester == academic_year_semester
                )
                logger.debug(
                    f"Applied academic year semester filter for schedule slots: {academic_year_semester}."
                )

            query = query.distinct()
            logger.debug("Applied DISTINCT clause to schedule slots query.")

            schedule_slots = db.exec(query).all()
            logger.info(
                f"Successfully retrieved {len(schedule_slots)} schedule slots for teacher ID {teacher_id}."
            )
            return schedule_slots
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error retrieving schedule slots for teacher ID {teacher_id} "
                f"(semester: {academic_year_semester or 'All'}): {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve teacher's schedule slots due to an internal error.",
            )

    def search_teachers_by_name(self, db: Session, name_query: str) -> list[Teacher]:
        logger.info(f"Attempting to search teachers by name query: '{name_query}'.")
        try:
            query = select(Teacher).where(col(Teacher.name).like(f"%{name_query}%"))
            teachers = db.exec(query).all()
            logger.info(
                f"Found {len(teachers)} teachers matching name query '{name_query}'."
            )
            return teachers
        except Exception as e:
            logger.error(
                f"Unexpected error searching teachers by name '{name_query}': {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to search teachers due to an internal error.",
            )
