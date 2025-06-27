import sys
import uuid
import logging
import time
import re
from typing import List, Tuple

from crawler.selenuim_helper import XPATH, TAG_NAME
from selenium.webdriver.chrome.webdriver import WebDriver as LocalWebDriver
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
from selenium.webdriver.remote.webelement import WebElement
from sqlalchemy.dialects import postgresql
from sqlmodel import select, col

from model import (
    Course,
    Teacher,
    CourseTeacher,
    CourseSchedule,
    CourseTypeEnum,
    WeekPatternEnum,
)
from core.database import get_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

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
    logging.info("Starting course data scraping process.")
    driver.get(URL)
    driver.switch_to.default_content()
    driver.switch_to.frame("304_top")

    college_select = driver.find_element(XPATH, "//*[@id='dpt_id']")
    college_options_len = len(college_select.find_elements(TAG_NAME, "option"))
    logging.info(f"Found {college_options_len} colleges.")

    for i in range(college_options_len):
        driver.switch_to.default_content()
        driver.switch_to.frame("304_top")
        college_select = driver.find_element(XPATH, "//*[@id='dpt_id']")
        college_option = college_select.find_elements(TAG_NAME, "option")[i]
        college_name = college_option.text.strip()

        if not college_name:
            continue

        logging.info(
            f"Processing College [{i + 1}/{college_options_len}]: {college_name}"
        )
        college_option.click()
        time.sleep(1.5)

        department_select = driver.find_element(XPATH, "//*[@id='unt_id']")
        department_options = department_select.find_elements(TAG_NAME, "option")

        for dept_index, department_option in enumerate(department_options):
            driver.switch_to.default_content()
            driver.switch_to.frame("304_top")

            current_department_option = driver.find_element(
                XPATH, f"//*[@id='unt_id']/option[{dept_index + 1}]"
            )
            department_name = current_department_option.text.strip()

            if not department_name:
                continue

            logging.info(f"--> Processing Department: {department_name}")
            current_department_option.click()
            time.sleep(1.5)

            driver.find_element(XPATH, "//*[@id='unit_serch']").click()
            driver.switch_to.default_content()
            driver.switch_to.frame("304_bottom")
            time.sleep(1.5)

            class_links = get_class_links(driver)
            class_links_count = len(class_links)
            logging.info(
                f"Found {class_links_count} class links for department {department_name}."
            )

            for j in range(class_links_count):
                class_link = get_class_links(driver)[j]
                class_link.click()
                time.sleep(1.5)

                parse_and_save_data(driver, college_name)

                driver.switch_to.default_content()
                driver.back()
                driver.switch_to.frame("304_bottom")
                time.sleep(1.5)

    logging.info("Finished all scraping tasks.")


def get_class_links(driver: LocalWebDriver | RemoteWebDriver) -> list[WebElement]:
    td_elements = driver.find_elements(TAG_NAME, "td")
    class_links: list[WebElement] = []
    for td in td_elements[4:]:
        if td.text == " ":
            break
        try:
            child = td.find_element(TAG_NAME, "div")
            class_links.append(child)
        except Exception:
            continue
    return class_links


def parse_and_save_data(driver: LocalWebDriver | RemoteWebDriver, college: str):
    try:
        class_name = driver.find_element(XPATH, "/html/body/font/font").text.strip()
        logging.info(f"Parsing data for class: {class_name}")
        data_table = driver.find_element(XPATH, "/html/body/font/form/table")
        row_elements = data_table.find_elements(TAG_NAME, "tr")
    except Exception as e:
        logging.error(
            f"Failed to find class name or data table on the page. Error: {e}"
        )
        return

    courses: list[Course] = []
    teachers: list[Teacher] = []
    course_teachers: list[CourseTeacher] = []
    course_schedules: list[CourseSchedule] = []
    teacher_course_pairs: list[tuple[str, uuid.UUID]] = []

    for row_element in row_elements[1:]:
        course = Course()
        course.class_name = class_name
        course.college = college
        column_elements = row_element.find_elements(TAG_NAME, "td")

        if not column_elements or not column_elements[0].text.strip():
            continue

        course.course_code = column_elements[0].text.strip()

        if "(停開)" in column_elements[1].text.strip():
            course.is_stop_opened = True
            course.name = column_elements[1].text.strip().replace("(停開)", "").strip()
        else:
            course.name = column_elements[1].text.strip()

        try:
            course.credit = int(float(column_elements[3].text.strip()))
        except (ValueError, IndexError):
            logging.warning(
                f"Could not parse credit for course {course.name}. Setting to 0."
            )
            course.credit = 0

        course_type_text = column_elements[5].text.strip()
        if course_type_text == "【必修】":
            course.course_type = CourseTypeEnum.REQUIRED
        elif course_type_text == "【選修】":
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
            logging.info(
                f"Course:{course.id} {course.course_code} {course.name} {course.college} {course.classroom}"
            )
    logging.info(f"Parsed {len(courses)} courses for class {class_name}.")

    if not courses:
        logging.info("No courses found to save.")
        return

    try:
        with next(get_db()) as db_session:
            logging.info("Starting database transaction...")
            db_session.add_all(courses)

            if teachers:
                stmt = postgresql.insert(Teacher).values(
                    [teacher.model_dump(exclude={"id"}) for teacher in teachers]
                )
                stmt = stmt.on_conflict_do_nothing(index_elements=["name"])
                db_session.exec(stmt)
                db_session.flush()

                db_teachers = db_session.exec(
                    select(Teacher).where(
                        col(Teacher.name).in_(
                            [name for name, _ in teacher_course_pairs]
                        )
                    )
                ).all()

                for teacher in db_teachers:
                    for name, course_id in teacher_course_pairs:
                        if teacher.name == name:
                            course_teachers.append(
                                CourseTeacher(
                                    course_id=course_id, teacher_id=teacher.id
                                )
                            )

            if course_teachers:
                db_session.add_all(course_teachers)
            if course_schedules:
                db_session.add_all(course_schedules)

            db_session.commit()
            logging.info("Database transaction committed successfully.")
    except Exception as e:
        logging.error(f"Error occurred while saving data: {e}", exc_info=True)


def parse_course_string(
    raw_string: str,
) -> Tuple[List[str], int | None, int | None, int | None, str, WeekPatternEnum]:
    clean_string = raw_string.strip()

    week_pattern = WeekPatternEnum.EVERY_WEEK
    if "(單週)" in clean_string:
        week_pattern = WeekPatternEnum.ODD_WEEKS
        clean_string = clean_string.replace("(單週)", " ").strip()
    elif "(雙週)" in clean_string:
        week_pattern = WeekPatternEnum.EVEN_WEEKS
        clean_string = clean_string.replace("(雙週)", " ").strip()

    if "時間未定" in clean_string:
        teacher_part = re.split(r"[/、\s]*時間未定", clean_string, 1)[0]
        cleaned_teacher_names = teacher_part.strip("、/, ")

        teachers = [
            t.strip() for t in re.split(r"[、,]", cleaned_teacher_names) if t.strip()
        ] or ["無"]

        location = "教室未定"
        loc_match = re.search(r"[(（](.*?)[)）]", clean_string)
        if loc_match:
            location = loc_match.group(1).strip()

        return teachers, None, None, None, location, week_pattern

    all_teachers = []
    all_locations = set()
    min_start_period, max_end_period = float("inf"), float("-inf")
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
        pattern = re.compile(r"\(([一二三四五六日])\)\s*(\d+)(?:-(\d+))?\((.*?)\)")
        matches = pattern.findall(time_loc_part)

        for match in matches:
            day_char, start_p_str, end_p_str, location = match

            if day_of_week is None:
                day_of_week = DAY_OF_WEEK_MAP.get(day_char)

            start_period = int(start_p_str)
            end_period = int(end_p_str) if end_p_str else start_period

            min_start_period = min(min_start_period, start_period)
            max_end_period = max(max_end_period, end_period)
            all_locations.add(location.strip())

    if not all_teachers and not all_locations and clean_string:
        return [clean_string], None, None, None, "", week_pattern

    final_start = int(min_start_period) if min_start_period != float("inf") else None
    final_end = int(max_end_period) if max_end_period != float("-inf") else None
    location_str = "、".join(sorted(all_locations))

    return (
        list(dict.fromkeys(all_teachers)),
        day_of_week,
        final_start,
        final_end,
        location_str,
        week_pattern,
    )
