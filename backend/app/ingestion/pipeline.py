import uuid
import os
from sqlalchemy.ext.asyncio import AsyncSession
from app.ingestion.pdf_parser import PDFParser
from app.ingestion.chunker import get_chunker
from app.ingestion.classifier import DocumentClassifier
from app.ingestion.metadata_extractor import MetadataExtractor
from app.ingestion.versioning import DocumentVersionManager
from app.db.models.document import Document, DocumentType, DocumentStatus
from app.db.models.chunk import Chunk as ChunkModel
from app.db.models.case import Case
from app.db.milvus import get_laws_collection, get_cases_collection
from app.config import settings
from app.utils.logger import logger
from langchain_openai import OpenAIEmbeddings
import json


class IngestionPipeline:

    def __init__(self):
        self.parser = PDFParser()
        self.classifier = DocumentClassifier()
        self.metadata_extractor = MetadataExtractor()
        self.version_manager = DocumentVersionManager()
        self.embedder = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )

    async def run(
        self,
        db: AsyncSession,
        file_path: str,
        filename: str,
        uploaded_by: uuid.UUID,
    ) -> Document:

        logger.info(f"Pipeline started for '{filename}'")
        doc_record = None

        try:
            # Step 1: Parse file
            parsed = self.parser.parse(file_path)

            # Step 2: Classify
            classification = self.classifier.classify(
                parsed.raw_text,
                file_metadata=parsed.file_metadata,
            )
            doc_type = DocumentType(classification.doc_type)
            visa_type = classification.detected_visa_type

            # Step 3: Version check
            version = await self.version_manager.get_or_create_version(
                db, filename, doc_type, visa_type
            )
            await self.version_manager.mark_previous_superseded(db, filename, version)

            # Step 4: Create document record
            doc_record = await self.version_manager.create_document_record(
                db=db,
                filename=filename,
                file_path=file_path,
                doc_type=doc_type,
                version=version,
                visa_type=visa_type,
                uploaded_by=uploaded_by,
            )

            doc_record.status = DocumentStatus.PROCESSING
            await db.commit()

            # Step 5: Chunk
            chunker = get_chunker(classification.doc_type)
            chunks = chunker.chunk(parsed)

            # Step 6: Setup Milvus collection
            milvus_collection = (
                get_laws_collection()
                if doc_type == DocumentType.LAW
                else get_cases_collection()
            )

            chunk_records = []
            milvus_data = {
                "chunk_id": [],
                "document_id": [],
                "text": [],
                "embedding": [],
                "visa_type": [],
                "doc_version": [],
                "section": [],
                "clause": [],
            }

            if doc_type == DocumentType.CASE:
                milvus_data.update({
                    "case_number": [],
                    "year": [],
                    "outcome": [],
                    "jurisdiction": [],
                })

            texts_to_embed = [c.text for c in chunks]

            # Step 7: Embed all chunks
            logger.info(f"Embedding {len(texts_to_embed)} chunks...")
            embeddings = await self.embedder.aembed_documents(texts_to_embed)

            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                metadata = self.metadata_extractor.extract(chunk)
                chunk_id = str(uuid.uuid4())

                # PostgreSQL chunk record
                chunk_record = ChunkModel(
                    document_id=doc_record.id,
                    chunk_index=i,
                    text=chunk.text,
                    section=metadata.section,
                    clause=metadata.clause,
                    visa_type=metadata.visa_type or visa_type,
                    doc_version=str(version),
                    token_count=len(chunk.text) // 4,
                )
                chunk_records.append(chunk_record)

                # safely convert section to string
                section_val = chunk.section
                if isinstance(section_val, list):
                    section_val = " | ".join(str(s) for s in section_val)
                section_val = (section_val or "")[:190]

                # safely convert clause to string
                clause_val = chunk.clause
                if isinstance(clause_val, list):
                    clause_val = " | ".join(str(c) for c in clause_val)
                clause_val = (clause_val or "")[:190]

                # Milvus data
                milvus_data["chunk_id"].append(chunk_id)
                milvus_data["document_id"].append(str(doc_record.id))
                milvus_data["text"].append(chunk.text[:65000])
                milvus_data["embedding"].append(embedding)
                milvus_data["visa_type"].append((metadata.visa_type or visa_type or "")[:90])
                milvus_data["doc_version"].append(str(version)[:40])
                milvus_data["section"].append(section_val)
                milvus_data["clause"].append(clause_val)

                if doc_type == DocumentType.CASE:
                    milvus_data["case_number"].append("")
                    milvus_data["year"].append(0)
                    milvus_data["outcome"].append("")
                    milvus_data["jurisdiction"].append("")

            # Step 8: Insert into Milvus
            entities = [
                milvus_data["chunk_id"],
                milvus_data["document_id"],
                milvus_data["section"],
                milvus_data["clause"],
                milvus_data["visa_type"],
                milvus_data["doc_version"],
                milvus_data["text"],
                milvus_data["embedding"],
            ]

            if doc_type == DocumentType.CASE:
                entities = [
                    milvus_data["chunk_id"],
                    milvus_data["document_id"],
                    milvus_data["case_number"],
                    milvus_data["visa_type"],
                    milvus_data["year"],
                    milvus_data["outcome"],
                    milvus_data["jurisdiction"],
                    milvus_data["text"],
                    milvus_data["embedding"],
                ]

            milvus_collection.insert(entities)
            milvus_collection.flush()
            logger.info(f"Inserted {len(chunks)} chunks into Milvus")

            # Step 9: Insert into PostgreSQL
            db.add_all(chunk_records)

            if doc_type == DocumentType.CASE:
                case_record = Case(
                    document_id=doc_record.id,
                    visa_type=visa_type,
                    cited_sections=json.dumps(
                        [ref for chunk in chunks
                         for ref in self.metadata_extractor.extract(chunk).cited_sections]
                    ),
                )
                db.add(case_record)

            doc_record.status = DocumentStatus.COMPLETED
            doc_record.total_chunks = len(chunks)
            await db.commit()

            logger.info(f"Pipeline completed for '{filename}' — {len(chunks)} chunks ingested")
            return doc_record

        except Exception as e:
            logger.error(f"Pipeline failed for '{filename}': {e}")
            if doc_record:
                doc_record.status = DocumentStatus.FAILED
                doc_record.error_message = str(e)
                await db.commit()
            raise