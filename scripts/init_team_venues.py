import sys
import json
import argparse
from pathlib import Path
from typing import Annotated, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if Path('.').resolve() != Path(__file__).resolve().parents[1]:
    sys.exit(f"Must be run from project root: {Path(__file__).resolve().parents[1]}")

from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from core.config.config_manager import get_config_manager
from core.store.postgres.postgresql_manager import get_postgresql_manager
from core.chat.llm import get_chat_llm_client
from core.store.postgres.models.fotmob.fixture import Fixture
from core.store.postgres.models.fotmob.team import TeamVenue
from core.store.postgres.models.common.league import SiteLeague
from sqlalchemy import func, union, select
from sqlalchemy.dialects.postgresql import insert


SYSTEM_PROMPT = """You are a football data assistant responsible for mapping football teams to their home city, one league at a time.

Workflow:
1. Use query_venue_status to show per-league progress summary, then wait for user instruction
2. When user selects a league (by name or ref_league_id), use fetch_unmapped_teams with that ref_league_id
3. For each team, determine the home city:
   - Club teams: city where their home stadium is located (e.g. Arsenal -> "London", PSG -> "Paris")
   - National teams: country name as it appears in Fotmob (e.g. Japan -> "Japan", Germany -> "Germany")
   - City/country name must match Fotmob's stadium.city / stadium.country naming convention
4. Show all mappings clearly before saving
5. Only call save_team_venues after user explicitly confirms
6. Repeat for the next league until done

Output rules:
- No emoji or special symbols
- Show team_id, team name, and assigned city for each entry
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_venue_status",
            "description": "Query mapping progress grouped by league, showing total teams, mapped count and pending count per league",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_unmapped_teams",
            "description": "Fetch teams in a specific league that do not yet have a home city mapping",
            "parameters": {
                "type": "object",
                "properties": {
                    "ref_league_id": {
                        "type": "integer",
                        "description": "The system ref_league_id to process",
                    },
                },
                "required": ["ref_league_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_team_venues",
            "description": "Save confirmed team-to-city mappings into the database. Must only be called after explicit user confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mappings": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "team_id": {"type": "integer"},
                                "city":    {"type": "string"},
                            },
                            "required": ["team_id", "city"],
                        },
                    }
                },
                "required": ["mappings"],
            },
        },
    },
]


class VenueState(TypedDict):
    messages: Annotated[list, add_messages]


def build_graph(db):
    llm = get_chat_llm_client().build_llm(max_tokens=4096).bind_tools(TOOLS)

    def agent(state: VenueState) -> dict:
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        return {"messages": [llm.invoke(messages)]}

    def tool_executor(state: VenueState) -> dict:
        last    = state["messages"][-1]
        results = []
        for tool_call in last.tool_calls:
            result = _execute_tool(db, tool_call["name"], tool_call["args"])
            results.append(ToolMessage(
                content=result,
                tool_call_id=tool_call["id"],
                name=tool_call["name"],
            ))
        return {"messages": results}

    def route_agent(state: VenueState) -> str:
        last = state["messages"][-1]
        return "tool_executor" if getattr(last, "tool_calls", None) else END

    def route_tool(state: VenueState) -> str:
        for msg in reversed(state["messages"]):
            if isinstance(msg, ToolMessage):
                try:
                    if "error" in json.loads(msg.content):
                        return END
                except Exception:
                    pass
                break
        return "agent"

    graph = StateGraph(VenueState)
    graph.add_node("agent",         agent)
    graph.add_node("tool_executor", tool_executor)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent",         route_agent, {"tool_executor": "tool_executor", END: END})
    graph.add_conditional_edges("tool_executor", route_tool,  {"agent": "agent", END: END})

    return graph.compile(checkpointer=MemorySaver())


def _execute_tool(db, name: str, args: dict) -> str:
    try:
        if name == "query_venue_status":
            with db.get_session() as session:
                home_teams = session.query(
                    SiteLeague.ref_league_id,
                    SiteLeague.league_name,
                    Fixture.home_id.label("team_id"),
                ).join(Fixture, Fixture.league_id == SiteLeague.league_id).filter(
                    SiteLeague.ref_league_id.isnot(None)
                ).distinct().subquery()

                away_teams = session.query(
                    SiteLeague.ref_league_id,
                    SiteLeague.league_name,
                    Fixture.away_id.label("team_id"),
                ).join(Fixture, Fixture.league_id == SiteLeague.league_id).filter(
                    SiteLeague.ref_league_id.isnot(None)
                ).distinct().subquery()

                all_teams = union(
                    select(home_teams),
                    select(away_teams),
                ).subquery()

                rows = session.query(
                    all_teams.c.ref_league_id,
                    func.max(all_teams.c.league_name).label("league_name"),
                    func.count(func.distinct(all_teams.c.team_id)).label("total"),
                    func.count(func.distinct(TeamVenue.team_id)).label("mapped"),
                ).outerjoin(
                    TeamVenue, all_teams.c.team_id == TeamVenue.team_id
                ).group_by(
                    all_teams.c.ref_league_id
                ).order_by(
                    func.count(func.distinct(all_teams.c.team_id)).desc()
                ).all()

            leagues = [
                {
                    "ref_league_id": row.ref_league_id,
                    "league_name":   row.league_name,
                    "total":         row.total,
                    "mapped":        row.mapped,
                    "pending":       row.total - row.mapped,
                }
                for row in rows
            ]
            return json.dumps({"leagues": leagues})

        if name == "fetch_unmapped_teams":
            ref_league_id = args["ref_league_id"]
            with db.get_session() as session:
                league_name = session.query(func.max(SiteLeague.league_name)).filter(
                    SiteLeague.ref_league_id == ref_league_id
                ).scalar()

                home_q = session.query(
                    Fixture.home_id.label("team_id"),
                    Fixture.home_team.label("team_name"),
                ).join(SiteLeague, SiteLeague.league_id == Fixture.league_id).filter(
                    SiteLeague.ref_league_id == ref_league_id
                ).distinct()

                away_q = session.query(
                    Fixture.away_id.label("team_id"),
                    Fixture.away_team.label("team_name"),
                ).join(SiteLeague, SiteLeague.league_id == Fixture.league_id).filter(
                    SiteLeague.ref_league_id == ref_league_id
                ).distinct()

                all_teams = home_q.union(away_q).subquery()

                rows = session.query(
                    all_teams.c.team_id,
                    all_teams.c.team_name,
                ).outerjoin(
                    TeamVenue, all_teams.c.team_id == TeamVenue.team_id
                ).filter(
                    TeamVenue.team_id.is_(None)
                ).all()

            return json.dumps({
                "ref_league_id": ref_league_id,
                "league_name":   league_name,
                "count":         len(rows),
                "teams":         [{"team_id": row.team_id, "team_name": row.team_name} for row in rows],
            })

        if name == "save_team_venues":
            mappings = args["mappings"]
            with db.get_session() as session:
                for mapping in mappings:
                    stmt = insert(TeamVenue).values(mapping)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=[TeamVenue.team_id.key],
                        set_={TeamVenue.city.key: mapping["city"]}
                    )
                    session.execute(stmt)
            return json.dumps({"ok": True, "saved": len(mappings)})

    except Exception as e:
        print(f"[tool:{name}] {e}", file=sys.stderr)
        return json.dumps({"error": str(e)})

    return json.dumps({"error": f"unknown tool: {name}"})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", "-c", type=str, default="configs/config.yml")
    args = parser.parse_args()

    get_config_manager().load_config(args.config)
    db = get_postgresql_manager()
    db.startup()

    compiled = build_graph(db)
    config   = {"configurable": {"thread_id": "init_team_venues"}}

    print("Team venue mapping assistant. Type 'quit' to exit.\n")

    result   = compiled.invoke({"messages": [HumanMessage(content="Query current mapping status grouped by league and show a summary.")]}, config)
    last_msg = result["messages"][-1]
    if last_msg.content:
        print(f"\n{last_msg.content}\n")

    while True:
        user_input = input(">>> ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            break

        result   = compiled.invoke({"messages": [HumanMessage(content=user_input)]}, config)
        last_msg = result["messages"][-1]
        if last_msg.content:
            print(f"\n{last_msg.content}\n")


if __name__ == "__main__":
    main()
