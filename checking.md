# check fotmob.fixture_raw
select match_date, last_kickoff_time, last_fetched_at, next_fetch_at, is_fetched, is_parsed from fotmob.fixture_raw order by match_date desc;

# check fotmob.match_raw
select match_id, kickoff_time, last_fetched_at, next_fetch_at, is_fetched, is_parsed from fotmob.match_raw order by kickoff_time desc;

# check oddsportal.league_raw
select last_fetched_at, next_fetch_at, is_fetched, is_parsed from oddsportal.league_raw;

# check oddsportal.leagues
select league_name, page_url, country_name, country_code, min_season, max_season from oddsportal.leagues where max_season is not null;

# check oddsportal.history_fixture_progress
select a.league_id, b.league_name, a.season, b.min_season, b.max_season, a.total, a.total_page, a.page_size, a.page  from oddsportal.history_fixture_progress a left join oddsportal.leagues b on a.league_id = b.league_id;

# check oddsportal.history_fixture_raw
select a.league_id, b.league_name, a.season, a.page, a.is_fetched, a.is_parsed, a.last_fetched_at, a.next_fetch_at, a.fetch_attempts from oddsportal.history_fixture_raw a left join oddsportal.leagues b on a.league_id = b.league_id order by league_name, season, page;

# check oddsportal.upcoming_fixture_raw
select a.league_id, b.league_name, a.season, a.is_fetched, a.is_parsed, a.last_fetched_at, a.next_fetch_at, a.fetch_attempts from oddsportal.upcoming_fixture_raw a left join oddsportal.leagues b on a.league_id = b.league_id order by league_name, season;

# check oddsportal.odds_raw
select match_code, kickoff_time, betting_type_id, scope_id, is_fetched, is_parsed, last_fetched_at, next_fetch_at from oddsportal.odds_raw order by kickoff_time desc;

# check oddsportal.season_raw
select league_id, league_name, last_fetched_at, next_fetch_at, is_fetched, is_parsed from oddsportal.season_raw order by last_fetched_at;