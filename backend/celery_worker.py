from app.tasks.celery_app import celery_app

# import all models so SQLAlchemy mapper initializes correctly
from app.db.models.user import User  # noqa
from app.db.models.document import Document  # noqa
from app.db.models.chunk import Chunk  # noqa
from app.db.models.case import Case  # noqa
from app.db.models.audit_log import AuditLog  # noqa
from app.db.models.feedback import Feedback  # noqa
from app.db.models.section_map import SectionMap  # noqa
from app.db.models.scrape_record import ScrapeRecord  # noqa
from app.db.models.matter import Matter  # noqa
from app.db.models.chat_query_meta import ChatQueryMeta  # noqa
from app.db.models.review_item import ReviewItem  # noqa
from app.db.models.policy_alert import PolicyAlert  # noqa

# import all task modules
import app.tasks.ingest_task      # noqa
import app.tasks.remap_task       # noqa
import app.tasks.feedback_task    # noqa
import app.tasks.scraper_task     # noqa

if __name__ == "__main__":
    celery_app.start()
