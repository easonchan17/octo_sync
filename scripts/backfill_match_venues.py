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

BATCH_SIZE = 200

def main():
    get_config_manager().load_config('configs/config.yml')
    logger = get_logger_manager().get_logger(__name__)

    db_manager = get_postgresql_manager()
    db_manager.startup()
    match_dao = MatchDao()
    parser = MatchParser()

    with db_manager.get_session() as session:
        total = session.query(MatchRaw.match_id)\
            .outerjoin(MatchVenue, MatchRaw.match_id == MatchVenue.match_id)\
            .filter(
                MatchRaw.is_parsed == True,
                MatchVenue.id.is_(None)
            ).count()

    logger.info(f"Found {total} matches pending venue backfill")

    success, skipped, offset = 0, 0, 0
    while offset < total:
        with db_manager.get_session() as session:
            batch = session.query(MatchRaw.match_id, MatchRaw.json_body)\
                .outerjoin(MatchVenue, MatchRaw.match_id == MatchVenue.match_id)\
                .filter(
                    MatchRaw.is_parsed == True,
                    MatchVenue.id.is_(None)
                ).order_by(MatchRaw.match_id).offset(offset).limit(BATCH_SIZE).all()

        for match_id, json_body in batch:
            stadium = (((json_body.get('content') or {}).get('matchFacts') or {}).get('infoBox') or {}).get('Stadium')
            if not stadium:
                skipped += 1
                continue
            venue = parser._parse_venue(match_id, stadium)
            match_dao.sync_parsed_data({"match_id": match_id, "venue": venue})
            success += 1

        offset += BATCH_SIZE
        logger.info(f"Progress: {min(offset, total)}/{total} (success={success}, skipped={skipped})")

    logger.info(f"Backfill complete: success={success}, skipped={skipped}, total={total}")

if __name__ == '__main__':
    main()
