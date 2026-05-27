from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.chunk import Chunk as ChunkModel
from app.db.models.section_map import SectionMap
from app.db.milvus import get_laws_collection
from app.utils.logger import logger
from langchain_openai import OpenAIEmbeddings
from app.config import settings
import re


class SectionMapper:
    """
    After a new USCIS policy doc is ingested, this runs in the background.
    It finds all old section references in case chunks and maps them
    to their current equivalent in the latest policy doc using semantic search.
    """

    SECTION_REF_PATTERN = re.compile(
        r"(Section\s+\d+[\.\d]*(?:,\s*Clause\s+\d+[\.\d]*)?|§\s*\d+[\.\d]*(?:\([a-z]\))?)",
        re.IGNORECASE
    )

    def __init__(self):
        self.embedder = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )

    async def run(self, db: AsyncSession):
        """
        Main entry point called as background task after ingestion.
        Finds all case chunks with old section refs and maps them.
        """
        logger.info("Section mapper started")

        # get all case chunks that have section references
        result = await db.execute(
            select(ChunkModel).where(ChunkModel.section != None)
        )
        case_chunks = result.scalars().all()

        mapped_count = 0
        for chunk in case_chunks:
            refs = self.SECTION_REF_PATTERN.findall(chunk.text)
            for ref in refs:
                already_mapped = await self._already_mapped(db, ref)
                if already_mapped:
                    continue

                current_chunk, score = await self._find_current_equivalent(ref)
                if current_chunk and score > 0.75:
                    await self._store_mapping(db, ref, current_chunk, score)
                    mapped_count += 1

        await db.commit()
        logger.info(f"Section mapper completed. Mapped {mapped_count} section references")

    async def _already_mapped(self, db: AsyncSession, ref: str) -> bool:
        """Check if this section ref already has a mapping."""
        result = await db.execute(
            select(SectionMap).where(SectionMap.old_section_ref == ref)
        )
        return result.scalars().first() is not None

    async def _find_current_equivalent(
        self,
        old_ref: str,
    ) -> tuple[ChunkModel | None, float]:
        """
        Embed the old section reference text and search Milvus laws collection
        for the semantically closest current chunk.
        """
        try:
            embedding = await self.embedder.aembed_query(old_ref)
            collection = get_laws_collection()

            results = collection.search(
                data=[embedding],
                anns_field="embedding",
                param={"metric_type": "COSINE", "params": {"ef": 64}},
                limit=1,
                output_fields=["chunk_id", "section", "clause", "doc_version"],
            )

            if not results or not results[0]:
                return None, 0.0

            top = results[0][0]
            score = top.score

            return top.entity, score

        except Exception as e:
            logger.error(f"Section mapper search failed for '{old_ref}': {e}")
            return None, 0.0

    async def _store_mapping(
        self,
        db: AsyncSession,
        old_ref: str,
        current_entity,
        score: float,
    ):
        """Store the resolved mapping in PostgreSQL."""
        mapping = SectionMap(
            old_section_ref=old_ref,
            current_section=current_entity.get("section"),
            current_doc_version=current_entity.get("doc_version"),
            similarity_score=score,
        )
        db.add(mapping)
        logger.debug(f"Mapped '{old_ref}' → '{mapping.current_section}' (score={score:.3f})")