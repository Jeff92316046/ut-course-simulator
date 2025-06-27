from typing import Optional
from pydantic import BaseModel, ConfigDict
import uuid
from datetime import datetime


class CourseTableCreate(BaseModel):
    name: str
    academic_year_semester: str


class CourseTableUpdate(BaseModel):
    name: str | None = None


class CourseTableResponse(BaseModel):
    id: uuid.UUID
    name: str
    academic_year_semester: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
