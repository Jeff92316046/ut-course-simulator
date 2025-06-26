import uuid
from fastapi import HTTPException, status
from sqlmodel import Session, col, distinct, func, select
from sqlalchemy.orm import selectinload
from model import Course, CourseSchedule, CourseTeacher, Teacher


class TeacherService:
    def get_teacher_all_courses(
        self,
        *,
        db: Session,
        teacher_id: uuid.UUID,
        academic_year_semester: str | None = None,
    ) -> list[Course]:
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
            query = query.where(Course.academic_year_semester == academic_year_semester)

        query = query.distinct()

        courses = db.exec(query).all()
        return courses

    def get_teacher_schedule_slots(
        self,
        *,
        db: Session,
        teacher_id: uuid.UUID,
        academic_year_semester: str | None = None,
    ) -> list[CourseSchedule]:
        teacher_exists = db.exec(
            select(Teacher.id).where(Teacher.id == teacher_id)
        ).first()
        if not teacher_exists:
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
            query = query.where(Course.academic_year_semester == academic_year_semester)

        query = query.distinct()
        schedule_slots = db.exec(query).all()
        return schedule_slots

    def search_teachers_by_name(self, db: Session, name_query: str) -> list[Teacher]:
        query = select(Teacher).where(col(Teacher.name).like(f"%{name_query.lower()}%"))
        teachers = db.exec(query).all()
        return teachers