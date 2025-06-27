import logging


def setup_logging():
    root_logger = logging.getLogger()

    root_logger.setLevel(logging.DEBUG)

    if not root_logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    return root_logger
