import uuid
from datetime import datetime, timezone
from typing import List
from enum import Enum

from sqlmodel import SQLModel, Field, Relationship, UniqueConstraint, DateTime, func


class CourseTypeEnum(str, Enum):
    REQUIRED = "required"
    ELECTIVE = "elective"


class WeekPatternEnum(str, Enum):
    EVERY_WEEK = "every_week"  # 每週
    ODD_WEEKS = "odd_weeks"  # 單週
    EVEN_WEEKS = "even_weeks"  # 雙週


def default_created_at() -> datetime:
    return datetime.now(tz=timezone.utc)


def default_updated_at() -> datetime:
    return datetime.now(tz=timezone.utc)


class CourseTeacher(SQLModel, table=True):
    __tablename__ = "course_teachers"

    id: int | None = Field(default=None, primary_key=True)
    course_id: uuid.UUID = Field(foreign_key="courses.id")
    teacher_id: uuid.UUID = Field(foreign_key="teachers.id")


class CourseSelection(SQLModel, table=True):
    __tablename__ = "course_selections"
    id: int | None = Field(default=None, primary_key=True)
    course_table_id: uuid.UUID = Field(foreign_key="course_tables.id")
    course_id: uuid.UUID = Field(foreign_key="courses.id")
    note: str | None = Field(default=None, max_length=500)  # 備註
    created_at: datetime = Field(default_factory=default_created_at)
    updated_at: datetime = Field(
        default_factory=default_created_at,
        sa_type=DateTime(),
        sa_column_kwargs={
            "onupdate": default_updated_at,
        },
    )

    course_table: "CourseTable" = Relationship(back_populates="course_selections")
    course: "Course" = Relationship()


class Teacher(SQLModel, table=True):
    __tablename__ = "teachers"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    name: str = Field(nullable=False, index=True, unique=True)  # 教師姓名

    courses: List["Course"] = Relationship(
        back_populates="teachers", link_model=CourseTeacher
    )


class CourseTable(SQLModel, table=True):
    __tablename__ = "course_tables"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    name: str = Field(nullable=False, default="我的選課表")
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    academic_year_semester: str = Field(
        nullable=False, index=True
    )  # e.g., '113-1', '113-2'
    created_at: datetime = Field(default_factory=default_created_at)
    updated_at: datetime = Field(
        default_factory=default_created_at,
        sa_type=DateTime(),
        sa_column_kwargs={
            "onupdate": default_updated_at,
        },
    )
    user: "User" = Relationship(back_populates="course_table_lists")
    course_selections: List["CourseSelection"] = Relationship(
        back_populates="course_table"
    )


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    email: str = Field(unique=True, index=True, nullable=False)
    name: str | None = Field(default=None)
    hashed_password: str = Field(nullable=False)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=default_created_at)
    updated_at: datetime = Field(
        default_factory=default_created_at,
        sa_type=DateTime(),
        sa_column_kwargs={
            "onupdate": default_updated_at,
        },
    )
    refresh_tokens: List["RefreshToken"] = Relationship(back_populates="user")

    course_table_lists: List["CourseTable"] = Relationship(back_populates="user")


class Course(SQLModel, table=True):
    __tablename__ = "courses"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    academic_year_semester: str = Field(
        nullable=False, index=True
    )  # e.g., '113-1', '113-2'
    course_code: str = Field(nullable=False, index=True)  # 課程代碼
    class_name: str = Field(nullable=False, index=True)  # 班級名稱
    college: str = Field(nullable=False, index=True)  # 學院
    name: str = Field(nullable=False, index=True)  # 課程名稱
    credit: int = Field(nullable=False)  # 學分
    classroom: str | None = Field(default=None)  # 課程地點
    field: str | None = Field(default=None, index=True)  # 領域
    campus_area: str | None = Field(default=None)  # 校區區域
    course_type: CourseTypeEnum = Field(nullable=False)  # 課程類型 (必修/選修)
    is_stop_opened: bool = Field(default=False)  # 是否已停開

    schedule_slots: List["CourseSchedule"] = Relationship(back_populates="course")

    teachers: List["Teacher"] = Relationship(
        back_populates="courses", link_model=CourseTeacher
    )

    __table_args__ = (
        UniqueConstraint(
            "academic_year_semester",
            "course_code",
            "class_name",
            "college",
            "name",
            name="uix_course_identity",
        ),
    )


class CourseSchedule(SQLModel, table=True):
    __tablename__ = "course_schedules"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    course_id: uuid.UUID = Field(foreign_key="courses.id", nullable=False)

    day_of_week: int = Field(nullable=True)
    start_period: int | None = Field(nullable=True)  # 起始節次
    end_period: int | None = Field(nullable=True)  # 結束節次

    week_pattern: WeekPatternEnum = Field(
        default=WeekPatternEnum.EVERY_WEEK, nullable=False
    )

    course: Course = Relationship(back_populates="schedule_slots")


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    hashed_token: str = Field(nullable=False, index=True)
    user_agent: str | None = Field(default=None)
    ip_address: str | None = Field(default=None)

    created_at: datetime = Field(default_factory=default_created_at)
    expires_at: datetime = Field(nullable=False)
    last_used_at: datetime | None = Field(default=None)
    revoked: bool = Field(default=False)

    user: User = Relationship(back_populates="refresh_tokens")
