from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.section_map import SectionMap
from app.db.models.chunk import Chunk as ChunkModel
from app.retrieval.hybrid_retriever import RetrievedChunk
from app.utils.logger import logger
import re


SECTION_REF_PATTERN = re.compile(
    r"(Section\s+\d+[\.\d]*(?:,\s*Clause\s+\d+[\.\d]*)?|§\s*\d+[\.\d]*(?:\([a-z]\))?)",
    re.IGNORECASE
)


class SectionResolver:
    """
    At query time, resolves old section references in case chunks
    to their current USCIS policy equivalents.

    Uses pre-computed mappings from the section_maps PostgreSQL table.
    Appends resolved current section text as additional context.

    Example:
    Input:  "...as per Section 1, Clause 1.3 of the 2020 policy..."
    Output: "...as per Section 1, Clause 1.3 of the 2020 policy...
             [CURRENT EQUIVALENT: Section 3, Clause 2.1 (2026)]
             [CURRENT TEXT: H-4 dependent spouses may apply for EAD if...]"
    """

    async def resolve(
        self,
        db: AsyncSession,
        chunks: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        """
        For each case chunk, find old section refs and append
        current equivalent text.
        """
        resolved_chunks = []

        for chunk in chunks:
            refs = SECTION_REF_PATTERN.findall(chunk.text)

            if not refs:
                resolved_chunks.append(chunk)
                continue

            enriched_text = chunk.text
            for ref in refs:
                mapping = await self._lookup_mapping(db, ref)
                if mapping:
                    current_chunk_text = await self._fetch_chunk_text(
                        db, mapping.current_chunk_id
                    )
                    enriched_text += (
                        f"\n\n[CURRENT EQUIVALENT OF '{ref}': "
                        f"{mapping.current_section} (v{mapping.current_doc_version})]"
                    )
                    if current_chunk_text:
                        enriched_text += (
                            f"\n[CURRENT POLICY TEXT: {current_chunk_text[:500]}...]"
                        )
                    logger.debug(
                        f"Resolved '{ref}' → "
                        f"'{mapping.current_section}' "
                        f"(score={mapping.similarity_score:.2f})"
                    )

            chunk.text = enriched_text
            resolved_chunks.append(chunk)

        return resolved_chunks

    async def _lookup_mapping(
        self,
        db: AsyncSession,
        ref: str,
    ) -> SectionMap | None:
        result = await db.execute(
            select(SectionMap)
            .where(SectionMap.old_section_ref == ref)
            .order_by(SectionMap.similarity_score.desc())
        )
        return result.scalars().first()

    async def _fetch_chunk_text(
        self,
        db: AsyncSession,
        chunk_id,
    ) -> str | None:
        result = await db.execute(
            select(ChunkModel.text).where(ChunkModel.id == chunk_id)
        )
        row = result.fetchone()
        return row[0] if row else None