import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if Path('.').resolve() != Path(__file__).resolve().parents[1]:
    sys.exit(f"Must be run from project root: {Path(__file__).resolve().parents[1]}")

from core.config.config_manager import get_config_manager
from core.logger.logger_manager import get_logger_manager
from core.store.postgres.postgresql_manager import get_postgresql_manager
from core.store.postgres.models.fotmob.match import MatchRaw, MatchVenue
from core.store.postgres.daos.fotmob import MatchDao
from core.tasks.sync.fotmob.parse_match import MatchParser

BATCH_SIZE = 500

def main():
    get_config_manager().load_config('configs/config.yml')
    logger = get_logger_manager().get_logger(__name__)

    db_manager = get_postgresql_manager()
    db_manager.startup()
    match_dao = MatchDao()
    parser = MatchParser()

    success, skipped = 0, 0
    while True:
        with db_manager.get_session() as session:
            batch = session.query(MatchRaw.match_id, MatchRaw.json_body)\
                .outerjoin(MatchVenue, MatchRaw.match_id == MatchVenue.match_id)\
                .filter(
                    MatchRaw.is_parsed == True,
                    MatchVenue.id.is_(None)
                ).order_by(MatchRaw.match_id).limit(BATCH_SIZE).all()

        if not batch:
            break

        for match_id, json_body in batch:
            stadium = (((json_body.get('content') or {}).get('matchFacts') or {}).get('infoBox') or {}).get('Stadium')
            venue = parser._parse_venue(match_id, stadium) if stadium else {"match_id": match_id}
            match_dao.sync_parsed_data({"match_id": match_id, "venue": venue})
            if stadium:
                success += 1
            else:
                skipped += 1

        logger.info(f"Batch done (success={success}, skipped={skipped})")

    logger.info(f"Backfill complete: success={success}, skipped={skipped}")

if __name__ == '__main__':
    main()
