import uuid
from fastapi import Query
from pydantic import BaseModel, SerializeAsAny, ConfigDict


class Teacher(BaseModel):
    id: uuid.UUID
    name: str
    model_config = ConfigDict(from_attributes=True)


class CourseSchedule(BaseModel):
    day_of_week: int | None
    start_period: int | None
    end_period: int | None
    model_config = ConfigDict(from_attributes=True)


class Course(BaseModel):
    id: uuid.UUID
    academic_year_semester: str
    course_code: str
    name: str
    credit: int
    college: str
    class_name: str
    classroom: str | None
    teachers: SerializeAsAny[list[Teacher]]
    schedule_slots: SerializeAsAny[list[CourseSchedule]]
    model_config = ConfigDict(from_attributes=True)


class PaginatedCourseResponse(BaseModel):
    total: int
    limit: int
    offset: int
    data: list[Course]
    model_config = ConfigDict(from_attributes=True)


class PaginationParams:
    def __init__(
        self,
        offset: int = 0,
        limit: int = Query(default=50, lte=100),
    ):
        self.offset = offset
        self.limit = limit
