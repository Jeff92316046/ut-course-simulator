from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone
from typing import List
from enum import Enum

from sqlmodel import SQLModel, Field, Relationship, func

class CourseTypeEnum(str, Enum):
    REQUIRED = "required"
    ELECTIVE = "elective"

def default_created_at() -> datetime:
    return datetime.now(tz=timezone.utc)

def default_expires_at() -> datetime:
    return datetime.now(tz=timezone.utc) + timedelta(days=14)

class CourseTeacher(SQLModel, table=True):
    __tablename__ = "course_teachers"

    id: int = Field(default=None, primary_key=True)
    course_id: uuid.UUID = Field(foreign_key="courses.id")
    teacher_id: uuid.UUID = Field(foreign_key="teachers.id")

    course: Course = Relationship(back_populates="teacher_links")
    teacher: Teacher = Relationship(back_populates="course_links")


class UserCourse(SQLModel, table=True):
    __tablename__ = "user_courses"
    id: int = Field(default=None, primary_key=True)
    course_list_id: uuid.UUID = Field(foreign_key="course_lists.id")
    course_id: uuid.UUID = Field(foreign_key="courses.id")

    enrollment_date: datetime = Field(default_factory=default_created_at)
    
    course_list: CourseList = Relationship(back_populates="user_courses")
    course: Course = Relationship()


class Teacher(SQLModel, table=True):
    __tablename__ = "teachers"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    name: str = Field(nullable=False, index=True)
    
    course_links: List[CourseTeacher] = Relationship(back_populates="teacher")
    courses: List[Course] = Relationship(back_populates="teachers", link_model=CourseTeacher)

class CourseList(SQLModel, table=True):
    __tablename__ = "course_lists"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    name: str = Field(nullable=False, default="我的選課表")
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    academic_year_semester: str = Field(nullable=False, index=True) # e.g., '113-1', '113-2'

    user: User = Relationship(back_populates="course_lists")
    user_courses: List[UserCourse] = Relationship(back_populates="course_list")


class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    email: str = Field(unique=True, index=True, nullable=False)
    name: str | None = Field(default=None)
    hashed_password: str = Field(nullable=False)
    is_active: bool = Field(default=True)
    
    refresh_tokens: List[RefreshToken] = Relationship(back_populates="user")
    
    course_lists: List[CourseList] = Relationship(back_populates="user")


class Course(SQLModel, table=True):
    __tablename__ = "courses"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    code: str = Field(nullable=False, unique=True, index=True) # 課程代碼
    name: str = Field(nullable=False, index=True) # 課程名稱
    credit: int = Field(nullable=False) # 學分
    field: str | None = Field(default=None, index=True) # 領域
    campus_area: str | None = Field(default=None) # 校區區域
    is_english_taught: bool = Field(default=False) # 是否為英文授課
    course_type: CourseTypeEnum = Field(nullable=False) # 課程類型 (必修/選修)
    academic_year_semester: str = Field(nullable=False, index=True) # e.g., '113-1', '113-2'

    schedule_slots: List[CourseSchedule] = Relationship(back_populates="course")

    teacher_links: List[CourseTeacher] = Relationship(back_populates="course")
    teachers: List[Teacher] = Relationship(back_populates="courses", link_model=CourseTeacher)


class CourseSchedule(SQLModel, table=True):
    __tablename__ = "course_schedules"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    course_id: uuid.UUID = Field(foreign_key="courses.id", nullable=False)
    
    day_of_week: int = Field(nullable=False)
    start_time: str = Field(nullable=False)
    end_time: str = Field(nullable=False)
    classroom: str | None = Field(default=None)
    
    course: Course = Relationship(back_populates="schedule_slots")


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    hashed_token: str = Field(nullable=False, index=True)
    user_agent: str | None = Field(default=None)
    ip_address: str | None = Field(default=None)
    
    created_at: datetime = Field(default_factory=default_created_at)
    expires_at: datetime = Field(default_factory=default_expires_at)
    last_used_at: datetime | None = Field(default=None)
    revoked: bool = Field(default=False)
    
    user: User = Relationship(back_populates="refresh_tokens")