import uuid

from sqlmodel import Session, col, select, func, distinct
from sqlalchemy.orm import selectinload, load_only

from model import Course, CourseSchedule, Teacher, CourseTeacher


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
        query = select(Course)
        query = query.options(
            selectinload(Course.teachers), selectinload(Course.schedule_slots)
        )
        needs_join = teacher_name or day_of_week is not None or start_period is not None
        if needs_join:
            query = query.distinct()

        if teacher_name:
            query = (
                query.join(CourseTeacher, CourseTeacher.course_id == Course.id)
                .join(Teacher, Teacher.id == CourseTeacher.teacher_id)
                .where(col(Teacher.name).like(f"%{teacher_name}%"))
            )

        if day_of_week is not None:
            query = query.join(
                CourseSchedule, CourseSchedule.course_id == Course.id, isouter=True
            ).where(CourseSchedule.day_of_week == day_of_week)

        if start_period is not None:
            if day_of_week is None:
                query = query.join(
                    CourseSchedule, CourseSchedule.course_id == Course.id, isouter=True
                )
            query = query.where(CourseSchedule.start_period == start_period)

        if academic_year_semester:
            query = query.where(Course.academic_year_semester == academic_year_semester)
        if course_code:
            query = query.where(Course.course_code == course_code)

        count_query = select(func.count()).select_from(
            query.options(load_only(Course.id)).subquery()
        )
        total_count = db.exec(count_query).one()

        paginated_query = query.offset(offset).limit(limit)
        courses = db.exec(paginated_query).all()

        return courses, total_count

    def get_teachers_for_course(
        self, *, db: Session, course_id: uuid.UUID
    ) -> Course | None:
        query = (
            select(Course)
            .where(Course.id == course_id)
            .options(selectinload(Course.teachers), selectinload(Course.schedule_slots))
        )
        course = db.exec(query).first()
        return course
