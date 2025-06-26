from pydantic import BaseModel, ConfigDict

import uuid
from model import WeekPatternEnum


class CourseScheduleResponse(BaseModel):
    course_id: uuid.UUID
    day_of_week: int | None
    start_period: int | None
    end_period: int | None
    week_pattern: WeekPatternEnum
    model_config = ConfigDict(from_attributes=True)
