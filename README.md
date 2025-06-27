# ut-course-simulator

ut-course-simulator is a backend system built with FastAPI and SQLModel for managing and querying university course data. It supports user authentication (with JWT and refresh tokens), course and teacher lookup, and personal course table management.

## Features

- JWT-based authentication with refresh tokens
- Course, teacher, and schedule querying
- User-defined course table creation and course selection management
- Automated course data crawler for up-to-date schedule imports

## Installation

- Requires Python 3.13
- Uses uv for dependency and virtual environment management

## Usage

To start the development server:

```
uv sync
fastapi dev src/main.py
```

Then open your browser and go to:

```
http://localhost:8000
```

## File Structure

```
ut-course-simulator/
├── src/
│   ├── api/              # API route definitions (e.g., auth, courses, teachers)
│   ├── core/             # Core utilities (e.g., security, config)
│   ├── crawler/          # Course crawler logic and scripts
│   ├── schemas/          # Pydantic models for request and response validation
│   ├── services/         # Business logic (e.g., authentication, course selection)
│   ├── model.py          # SQLModel database models
│   └── main.py           # FastAPI app entry point
├── .env.sample           # Sample environment variable file
├── Dockerfile            # Docker image build configuration
├── docker-compose.yml    # Docker Compose services configuration
├── uv.lock               # Dependency lock file managed by `uv`
└── pyproject.toml        # Project metadata and dependencies
```

## License

This project is licensed under the MIT License.

## Disclaimer

This project and its crawler functionalities are for educational purposes only.
All data retrieved is used solely for learning, testing, or research.
No data is stored or redistributed for commercial use.

## Contact

Created by Your Name - you@example.com
