import uuid
from fastapi import Depends, HTTPException, status
from sqlmodel import select, Session
import logging

from core.security import oauth2_scheme, decode_access_token
from core.database import get_db

from model import CourseSelection, CourseTable, User

logger = logging.getLogger(__name__)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """
    Retrieves the current authenticated user from the provided OAuth2 token.
    """
    logger.debug("Attempting to get current user from token.")
    try:
        payload = decode_access_token(token)
    except Exception as e:
        logger.warning(f"Access token decoding failed: {e}", exc_info=False)
        raise HTTPException(status_code=401, detail="Invalid or expired access token")

    user_id = payload.get("sub")
    if not user_id:
        logger.warning("Token payload does not contain a user ID (sub claim).")
        raise HTTPException(status_code=401, detail="Invalid authentication payload")

    user = db.exec(select(User).where(User.id == user_id)).first()
    if not user:
        logger.warning(f"User with ID {user_id} found in token but not in database.")
        raise HTTPException(status_code=404, detail="User not found")

    logger.debug(f"Current user ID {user.id} retrieved successfully.")
    return user


def get_owned_course_table(
    table_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CourseTable:
    """
    Retrieves a course table by ID, ensuring it is owned by the current user.
    """
    logger.debug(
        f"Attempting to retrieve course table ID {table_id} for user ID {current_user.id}."
    )
    course_table = db.exec(
        select(CourseTable).where(
            CourseTable.id == table_id, CourseTable.user_id == current_user.id
        )
    ).first()
    if not course_table:
        logger.warning(
            f"Course table ID {table_id} not found or not owned by user ID {current_user.id}."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course table not found."
        )
    logger.debug(
        f"Course table ID {table_id} successfully retrieved and owned by user ID {current_user.id}."
    )
    return course_table


def get_owned_course_selection(
    selection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CourseSelection:
    """
    Retrieves a course selection by ID, ensuring it belongs to a course table owned by the current user.
    """
    logger.debug(
        f"Attempting to retrieve course selection ID {selection_id} for user ID {current_user.id}."
    )

    selection = db.exec(
        select(CourseSelection).where(CourseSelection.id == selection_id)
    ).first()
    if not selection:
        logger.warning(f"Course selection ID {selection_id} not found in database.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course selection not found."
        )

    course_table = db.exec(
        select(CourseTable).where(
            CourseTable.id == selection.course_table_id,
            CourseTable.user_id == current_user.id,
        )
    ).first()

    if not course_table:
        logger.warning(
            f"Course selection ID {selection_id} found but its associated course table ({selection.course_table_id}) is not owned by user ID {current_user.id}."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course selection not found"
        )

    logger.debug(
        f"Course selection ID {selection_id} successfully retrieved and owned by user ID {current_user.id}."
    )
    return selection
