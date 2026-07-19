import csv
import json
import logging
from datetime import datetime
from io import StringIO
from typing import List

from schemas.review import Review

logger = logging.getLogger(__name__)


def _try_parse_date(value: str) -> datetime:
    """Try to parse a date string with multiple common formats.

    Returns parsed datetime on success, or datetime.now() as fallback.
    """
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",      # 2024-01-15T10:30:00+00:00
        "%Y-%m-%dT%H:%M:%S",         # 2024-01-15T10:30:00
        "%Y-%m-%d %H:%M:%S",         # 2024-01-15 10:30:00
        "%Y-%m-%d",                  # 2024-01-15
        "%Y/%m/%d",                  # 2024/01/15
        "%m/%d/%Y",                  # 01/15/2024
        "%d/%m/%Y",                  # 15/01/2024
    ]
    for fmt in formats:
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    logger.debug(f"Could not parse date '{value}', using current time as fallback")
    return datetime.now()


def _parse_csv(data: str) -> List[Review]:
    """Parse CSV data and return a list of Review objects.

    Expected header: id, rating, title, content, author, date, version, app_id
    At minimum, ``content`` must be present and non-empty.
    """
    reader = csv.DictReader(StringIO(data))
    if not reader.fieldnames:
        raise ValueError("CSV data has no header row")

    fieldnames = [f.strip().lower() for f in reader.fieldnames]

    if "content" not in fieldnames:
        raise ValueError("CSV must contain a 'content' column")

    reviews: List[Review] = []
    skipped = 0

    for row_num, row in enumerate(reader, start=2):  # header is row 1
        # Normalise keys to lowercase
        row = {k.strip().lower(): v.strip() if v else v for k, v in row.items()}

        content = row.get("content", "")
        if not content:
            logger.warning(f"Row {row_num}: empty content, skipping")
            skipped += 1
            continue

        try:
            review = Review(
                id=row.get("id", f"csv-{row_num}"),
                app_id=row.get("app_id", "imported"),
                rating=int(row.get("rating", 3)),
                title=row.get("title") or None,
                content=content,
                author=row.get("author", "unknown"),
                date=_try_parse_date(row.get("date", "")),
                version=row.get("version") or None,
            )
            reviews.append(review)
        except (ValueError, TypeError) as e:
            logger.warning(f"Row {row_num}: invalid data ({e}), skipping")
            skipped += 1
            continue

    logger.info(
        "CSV parsed: %d reviews imported, %d skipped (format: csv)",
        len(reviews),
        skipped,
    )
    return reviews


def _parse_json(data: str) -> List[Review]:
    """Parse JSON data and return a list of Review objects.

    Supports two shapes:
      - Array:  ``[{"id": "1", ...}, ...]``
      - Object: ``{"reviews": [...]}``
    """
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e

    # Unwrap {"reviews": [...]} shape
    if isinstance(parsed, dict):
        if "reviews" in parsed:
            parsed = parsed["reviews"]
        else:
            raise ValueError(
                "JSON object must contain a 'reviews' key, e.g. {\"reviews\": [...]}"
            )

    if not isinstance(parsed, list):
        raise ValueError("JSON data must be a list or contain a 'reviews' list")

    reviews: List[Review] = []
    skipped = 0

    for idx, item in enumerate(parsed):
        if not isinstance(item, dict):
            logger.warning(f"Item {idx}: not a JSON object, skipping")
            skipped += 1
            continue

        content = item.get("content", "")
        if not content:
            logger.warning(f"Item {idx}: empty content, skipping")
            skipped += 1
            continue

        try:
            date_value = item.get("date")
            if isinstance(date_value, str):
                parsed_date = _try_parse_date(date_value)
            elif isinstance(date_value, datetime):
                parsed_date = date_value
            else:
                parsed_date = datetime.now()

            review = Review(
                id=str(item.get("id", f"json-{idx + 1}")),
                app_id=str(item.get("app_id", "imported")),
                rating=int(item.get("rating", 3)),
                title=item.get("title") or None,
                content=content,
                author=str(item.get("author", "unknown")),
                date=parsed_date,
                version=item.get("version") or None,
            )
            reviews.append(review)
        except (ValueError, TypeError) as e:
            logger.warning(f"Item {idx}: invalid data ({e}), skipping")
            skipped += 1
            continue

    logger.info(
        "JSON parsed: %d reviews imported, %d skipped (format: json)",
        len(reviews),
        skipped,
    )
    return reviews


def _detect_format(data: str) -> str:
    """Detect whether *data* is JSON or CSV.

    Returns ``"json"`` or ``"csv"``.
    """
    stripped = data.strip()
    if not stripped:
        raise ValueError("Input data is empty")

    if stripped[0] in ("[", "{"):
        return "json"
    return "csv"


def import_reviews(data: str) -> List[Review]:
    """Import reviews from JSON or CSV data.

    The format is auto-detected:
      - **JSON**: an array of review objects, or an object with a ``"reviews"`` key.
      - **CSV**: header row with columns like ``id, rating, title, content, author, date, version, app_id``.

    Required field: ``content`` must be present and non-empty.

    Returns:
        List of validated :class:`Review` objects.  Invalid rows are skipped with
        a warning log.  Empty input returns an empty list.

    Raises:
        ValueError: If the format cannot be identified or the data is malformed
            beyond individual-row recovery.
    """
    stripped = data.strip()
    if not stripped:
        logger.warning("import_reviews called with empty data, returning empty list")
        return []

    fmt = _detect_format(stripped)
    logger.info("Detected format: %s", fmt)

    if fmt == "json":
        return _parse_json(stripped)
    else:
        return _parse_csv(stripped)
