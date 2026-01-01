from core.domain.enums import LeagueID

LEAGUE_METADATA = {
    LeagueID.EPL: {
        "name_cn": "英超",
        "name_en": "Premier League",
        "mappings": {
            "fbref": "9",
            "fotmob": "47"
        }
    },
    LeagueID.LALIGA: {
        "name_cn": "西甲",
        "name_en": "LaLiga",
        "mappings": {
            "fbref": "",
            "fotmob": ""
        }
    }
}
