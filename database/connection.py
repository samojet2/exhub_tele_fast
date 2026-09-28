from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker


DATABASE_URL = "sqlite:////app/data/telegram_service.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
    },
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):

    cursor = dbapi_connection.cursor()

    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")

    cursor.close()


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)