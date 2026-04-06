"""PostgreSQL 연결 관리 모듈.

환경변수로 DB 설정을 주입받아 커넥션을 생성한다.
커넥션 수명 관리는 managed_connection() context manager를 사용한다.
"""

import logging
import os
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass

import psycopg2
import psycopg2.extensions

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    dbname: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        return cls(
            host=os.environ.get("DB_HOST", "localhost"),
            port=int(os.environ.get("DB_PORT", "5432")),
            dbname=os.environ.get("DB_NAME", "news_collector"),
            user=os.environ.get("DB_USER", os.environ.get("USER", "postgres")),
            password=os.environ.get("DB_PASSWORD", ""),
        )


def get_connection(config: DatabaseConfig) -> psycopg2.extensions.connection:
    """psycopg2 커넥션을 생성하고 반환한다.

    Args:
        config: DB 접속 설정

    Returns:
        psycopg2 connection (autocommit=False)

    Raises:
        psycopg2.OperationalError: DB 접속 실패 시
    """
    conn = psycopg2.connect(
        host=config.host,
        port=config.port,
        dbname=config.dbname,
        user=config.user,
        password=config.password,
    )
    conn.autocommit = False
    logger.debug("DB 커넥션 생성 완료 (host=%s, dbname=%s)", config.host, config.dbname)
    return conn


@contextmanager
def managed_connection(
    config: DatabaseConfig,
) -> Generator[psycopg2.extensions.connection, None, None]:
    """커넥션 수명을 관리하는 context manager.

    with 블록 종료 시 커넥션을 닫는다.
    예외가 발생해도 커넥션 누수가 발생하지 않는다.

    Usage:
        with managed_connection(config) as conn:
            ...

    Raises:
        psycopg2.OperationalError: DB 접속 실패 시
    """
    conn: psycopg2.extensions.connection | None = None
    try:
        conn = get_connection(config)
        yield conn
    except psycopg2.OperationalError:
        logger.exception("DB 접속 실패 (host=%s, dbname=%s)", config.host, config.dbname)
        raise
    finally:
        if conn is not None and not conn.closed:
            conn.close()
            logger.debug("DB 커넥션 종료")
