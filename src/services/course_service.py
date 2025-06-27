import uuid
import logging

from sqlmodel import Session, col, select, func, distinct
from sqlalchemy.orm import selectinload, load_only

from model import Course, CourseSchedule, Teacher, CourseTeacher

logger = logging.getLogger(__name__)


class CourseService:
    def get_courses(
        self,
        *,
        db: Session,
        academic_year_semester: str | None = None,
        course_code: str | None = None,
        teacher_name: str | None = None,
        day_of_week: int | None = None,
        start_period: int | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[Course], int]:
        logger.info(
            f"Fetching courses with filters: "
            f"semester='{academic_year_semester or 'N/A'}', code='{course_code or 'N/A'}', "
            f"teacher='{teacher_name or 'N/A'}', day='{day_of_week or 'N/A'}', "
            f"period='{start_period or 'N/A'}', limit={limit}, offset={offset}."
        )

        query = select(Course)
        query = query.options(
            selectinload(Course.teachers), selectinload(Course.schedule_slots)
        )
        needs_join = teacher_name or day_of_week is not None or start_period is not None
        if needs_join:
            query = query.distinct()
            logger.debug("Applying DISTINCT due to joins for teacher/schedule filters.")

        if teacher_name:
            query = (
                query.join(CourseTeacher, CourseTeacher.course_id == Course.id)
                .join(Teacher, Teacher.id == CourseTeacher.teacher_id)
                .where(col(Teacher.name).like(f"%{teacher_name}%"))
            )
            logger.debug(f"Added teacher name filter: '{teacher_name}'.")

        if day_of_week is not None:
            query = query.join(
                CourseSchedule, CourseSchedule.course_id == Course.id, isouter=True
            ).where(CourseSchedule.day_of_week == day_of_week)
            logger.debug(f"Added day_of_week filter: {day_of_week}.")

        if start_period is not None:
            if day_of_week is None:
                query = query.join(
                    CourseSchedule, CourseSchedule.course_id == Course.id, isouter=True
                )
            query = query.where(CourseSchedule.start_period == start_period)
            logger.debug(f"Added start_period filter: {start_period}.")

        if academic_year_semester:
            query = query.where(Course.academic_year_semester == academic_year_semester)
            logger.debug(
                f"Added academic_year_semester filter: '{academic_year_semester}'."
            )
        if course_code:
            query = query.where(Course.course_code == course_code)
            logger.debug(f"Added course_code filter: '{course_code}'.")

        try:
            count_query = select(func.count()).select_from(
                query.options(load_only(Course.id)).subquery()
            )
            total_count = db.exec(count_query).one()
            logger.debug(f"Total count for filtered courses: {total_count}.")

            paginated_query = query.offset(offset).limit(limit)
            courses = db.exec(paginated_query).all()

            logger.info(
                f"Successfully retrieved {len(courses)} courses (total {total_count}) with applied filters."
            )
            return courses, total_count
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while getting courses: {e}",
                exc_info=True,
            )
            raise

    def get_teachers_for_course(
        self, *, db: Session, course_id: uuid.UUID
    ) -> Course | None:
        logger.info(f"Attempting to retrieve teachers for course ID: {course_id}.")
        try:
            query = (
                select(Course)
                .where(Course.id == course_id)
                .options(
                    selectinload(Course.teachers), selectinload(Course.schedule_slots)
                )
            )
            course = db.exec(query).first()

            if course:
                logger.info(
                    f"Successfully retrieved course {course_id} and its teachers."
                )
            else:
                logger.warning(f"Course ID {course_id} not found.")
            return course
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while getting teachers for course ID {course_id}: {e}",
                exc_info=True,
            )
            raise
