import uuid
from crawler.selenuim_helper import XPATH, TAG_NAME
from selenium.webdriver.chrome.webdriver import WebDriver as LocalWebDriver
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
from selenium.webdriver.remote.webelement import WebElement
import time

from model import (
    Course,
    Teacher,
    CourseTeacher,
    CourseSchedule,
    CourseTypeEnum,
    WeekPatternEnum,
)

from typing import List, Tuple
import re

from sqlalchemy.dialects import postgresql
from sqlmodel import select, col
from core.database import get_db

URL = "https://shcourse.utaipei.edu.tw/utaipei/ag_pro/ag304_index.jsp"

DAY_OF_WEEK_MAP = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "日": 7,
}


def get_course_data(driver: LocalWebDriver | RemoteWebDriver):
    driver.get(URL)
    driver.switch_to.default_content()
    driver.switch_to.frame("304_top")
    college_select = driver.find_element(XPATH, "//*[@id='dpt_id']")  # collage select
    college_options_len = len(college_select.find_elements(TAG_NAME, "option"))
    for i in range(college_options_len):
        driver.switch_to.default_content()
        driver.switch_to.frame("304_top")
        college_select = driver.find_element(
            XPATH, "//*[@id='dpt_id']"
        )  # collage select
        college_option = college_select.find_elements(TAG_NAME, "option")[i]
        college_name = college_option.text.strip()
        college_option.click()
        time.sleep(1.5)
        department_select = driver.find_element(XPATH, "//*[@id='unt_id']")
        department_options = department_select.find_elements(TAG_NAME, "option")
        for department_option in department_options:
            driver.switch_to.default_content()
            driver.switch_to.frame("304_top")
            department_option.click()
            time.sleep(1.5)
            driver.find_element(XPATH, "//*[@id='unit_serch']").click()
            driver.switch_to.default_content()
            driver.switch_to.frame("304_bottom")
            time.sleep(1.5)
            class_links_count = len(get_class_links(driver))
            for i in range(class_links_count):
                class_link = get_class_links(driver)[i]
                class_link.click()
                time.sleep(1.5)
                parse_and_save_data(driver, college_name)
                driver.switch_to.default_content()
                driver.back()
                driver.switch_to.frame("304_bottom")
                time.sleep(1.5)


def get_class_links(driver: LocalWebDriver | RemoteWebDriver) -> list[WebElement]:
    td_elements = driver.find_elements(TAG_NAME, "td")
    class_links: list[WebElement] = []
    for td in td_elements[4:]:
        if td.text == " ":
            break
        child = td.find_element(TAG_NAME, "div")
        class_links.append(child)
    # print(f"Found {len(class_links)} class links.")
    return class_links


def parse_and_save_data(driver: LocalWebDriver | RemoteWebDriver, colleage: str):
    class_name = driver.find_element(XPATH, "/html/body/font/font").text.strip()
    data_table = driver.find_element(XPATH, "/html/body/font/form/table")
    row_elements = data_table.find_elements(TAG_NAME, "tr")
    courses: list[Course] = []
    teachers: list[Teacher] = []
    course_teachers: list[CourseTeacher] = []
    course_schedules: list[CourseSchedule] = []
    teacher_course_pairs: list[tuple[str, uuid.UUID]] = []
    for row_element in row_elements[1:]:
        course = Course()
        course.class_name = class_name
        course.college = colleage
        column_elements = row_element.find_elements(TAG_NAME, "td")
        course.course_code = column_elements[0].text.strip()

        if "(停開)" in column_elements[1].text.strip():
            course.is_stop_opened = True
            course.name = column_elements[1].text.strip().replace("(停開)", "").strip()
        else:
            course.name = column_elements[1].text.strip()

        course.credit = int(float(column_elements[3].text.strip()))

        if column_elements[5].text.strip() == "【必修】":
            course.course_type = CourseTypeEnum.REQUIRED
        elif column_elements[5].text.strip() == "【選修】":
            course.course_type = CourseTypeEnum.ELECTIVE

        course.campus_area = column_elements[7].text.strip()

        if column_elements[8].text.strip():
            (
                teacher_list,
                day_of_week,
                start_period,
                end_period,
                location,
                week_pattern,
            ) = parse_course_string(column_elements[8].text.strip())
            for teacher_name in teacher_list:
                teacher = Teacher(name=teacher_name)
                teachers.append(teacher)
                teacher_course_pairs.append((teacher_name, course.id))
            course.classroom = location
            course_schedule = CourseSchedule(
                day_of_week=day_of_week,
                start_period=start_period,
                end_period=end_period,
                week_pattern=week_pattern,
                course_id=course.id,
            )
            course_schedules.append(course_schedule)
        else:
            course.classroom = "教室未定"
        course.academic_year_semester = "114-1"
        course.field = column_elements[9].text.strip()
        courses.append(course)
    for course in courses:
        print(f"Course: {course.college} {course.class_name} {course.name}")
    try:
        with next(get_db()) as db_session:
            db_session.add_all(courses)
            stmt = postgresql.insert(Teacher).values(
                [teacher.model_dump(exclude={"id"}) for teacher in teachers]
            )
            stmt = stmt.on_conflict_do_nothing(index_elements=["name"])
            db_session.exec(stmt)
            db_session.flush()
            db_teachers = db_session.exec(
                select(Teacher).where(
                    col(Teacher.name).in_([name for name, _ in teacher_course_pairs])
                )
            ).all()
            for teacher in db_teachers:
                for name, course_id in teacher_course_pairs:
                    if teacher.name == name:
                        course_teachers.append(
                            CourseTeacher(course_id=course_id, teacher_id=teacher.id)
                        )
            db_session.add_all(course_teachers)
            db_session.add_all(course_schedules)
            db_session.commit()
    except Exception as e:
        print(f"Error occurred while saving data: {e}")
        db_session.rollback()


def parse_course_string(
    raw_string: str,
) -> Tuple[List[str], int | None, int | None, int | None, str, WeekPatternEnum]:
    clean_string = raw_string.strip()

    week_pattern = WeekPatternEnum.EVERY_WEEK
    if "(單週)" in clean_string:
        week_pattern = WeekPatternEnum.ODD_WEEKS
        clean_string = (
            clean_string.replace("(單週)", " ").replace("(雙週)", " ").strip()
        )
    elif "(雙週)" in clean_string:
        week_pattern = WeekPatternEnum.EVEN_WEEKS
        clean_string = (
            clean_string.replace("(雙週)", " ").replace("(單週)", " ").strip()
        )

    if "時間未定" in clean_string:
        teacher_part = re.split(r"[/、\s]*時間未定", clean_string, 1)[0]
        cleaned_teacher_names = teacher_part.strip("、/, ")

        if not cleaned_teacher_names:
            teachers = ["無"]
        else:
            teachers = [
                t.strip()
                for t in re.split(r"[、,]", cleaned_teacher_names)
                if t.strip()
            ]

        location = "教室未定"
        loc_match = re.search(r"[(（](.*?)[)）]", clean_string)
        if loc_match:
            location_content = loc_match.group(1).strip()
            if "教室未定" not in location_content:
                location = location_content
        elif "教室未定" in clean_string:
            location = "教室未定"

        return teachers, None, None, None, location, week_pattern

    all_teachers = []
    all_locations = set()
    min_start_period = float("inf")
    max_end_period = float("-inf")
    day_of_week = None

    lines = [line.strip() for line in clean_string.split("\n") if line.strip()]

    for line in lines:
        teacher_match = re.match(r"(.+?)\s*\(", line)
        if not teacher_match:
            if line.strip() and all_teachers:
                all_teachers.append(line.strip())
            continue

        potential_name = teacher_match.group(1)
        teacher_name = re.sub(r"\s+\d+$", "", potential_name).strip()
        all_teachers.append(teacher_name)

        time_loc_part = line[teacher_match.end(1) :].strip()

        pattern = re.compile(
            r"\(([一二三四五六日])\)"
            r"\s*(\d+)"
            r"(?:-(\d+))?"
            r"\((.*?)\)"
        )

        matches: list[str] = pattern.findall(time_loc_part)

        for match in matches:
            day_char, start_p_str, end_p_str, location = match

            if day_of_week is None:
                day_of_week = DAY_OF_WEEK_MAP.get(day_char)

            start_period = int(start_p_str)
            end_period = int(end_p_str) if end_p_str else start_period

            min_start_period = min(min_start_period, start_period)
            max_end_period = max(max_end_period, end_period)

            all_locations.add(location.strip())

    if not all_teachers and not all_locations:
        if clean_string:
            return [clean_string], None, None, None, "", week_pattern
        else:
            return [], None, None, None, "", week_pattern

    if min_start_period == float("inf"):
        return list(dict.fromkeys(all_teachers)), None, None, None, "", week_pattern

    location_str = "、".join(sorted(all_locations))

    return (
        list(dict.fromkeys(all_teachers)),
        day_of_week,
        int(min_start_period),
        int(max_end_period),
        location_str,
        week_pattern,
    )
