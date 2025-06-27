from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, SerializeAsAny

from schemas.course import CourseSchedule


class CourseSelectionCreate(BaseModel):
    course_id: uuid.UUID
    note: str | None = None


class CourseSelectionUpdate(BaseModel):
    note: str | None = None


class BriefCourseInfo(BaseModel):
    id: uuid.UUID
    course_code: str
    name: str
    credit: int
    schedule_slots: SerializeAsAny[list[CourseSchedule]]
    model_config = ConfigDict(from_attributes=True)


class CourseSelectionResponse(BaseModel):
    id: uuid.UUID
    course_table_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    note: str | None = None
    course: BriefCourseInfo
    model_config = ConfigDict(from_attributes=True)
