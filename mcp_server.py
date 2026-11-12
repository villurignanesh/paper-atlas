"""Local stdio MCP adapter for the Paper Atlas query core."""

from functools import lru_cache
import os
from typing import Annotated, Any

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from paper_atlas.query_core import PaperCorpus


mcp = MCPServer("Paper Atlas")


@lru_cache(maxsize=1)
def _corpus() -> PaperCorpus:
    data_dir = os.environ.get("PAPER_ATLAS_DATA_DIR")
    if not data_dir:
        raise ToolError("Set PAPER_ATLAS_DATA_DIR to the local processed data directory.")
    try:
        return PaperCorpus(data_dir)
    except FileNotFoundError as exc:
        raise ToolError(f"Paper Atlas corpus is incomplete: {exc}") from exc


@mcp.tool()
def search_papers(
    query: Annotated[str, Field(description="Words to find in titles, authors, keywords, or abstracts.")],
    venue: str | None = None,
    year: int | None = None,
    limit: Annotated[int, Field(ge=1, le=50)] = 10,
) -> dict[str, Any]:
    """Search source metadata and abstracts lexically; results are not full-text verified."""
    try:
        return _corpus().search_papers(query, venue=venue, year=year, limit=limit)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool()
def get_paper(paper_id: str) -> dict[str, Any]:
    """Get one paper's source link, metadata, and available abstract; no PDF evidence."""
    try:
        return _corpus().get_paper(paper_id)
    except LookupError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool()
def related_papers(
    paper_id: str,
    limit: Annotated[int, Field(ge=1, le=50)] = 10,
) -> dict[str, Any]:
    """Find same-leaf-cluster papers, newest first; this does not imply support or citation."""
    try:
        return _corpus().related_papers(paper_id, limit=limit)
    except LookupError as exc:
        raise ToolError(str(exc)) from exc


if __name__ == "__main__":
    mcp.run()
