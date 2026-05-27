import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from app.retrieval.hybrid_retriever import RetrievedChunk
from app.utils.logger import logger
from langchain_openai import OpenAIEmbeddings
from app.config import settings


class CaseClustering:
    """
    Groups similar case chunks together using cosine similarity.
    Picks the highest-scoring representative from each cluster.

    This prevents GPT from receiving 8 chunks about the same
    ruling — massive token waste and repetitive answers.

    Algorithm:
    1. Embed all case chunks
    2. Build cosine similarity matrix
    3. Greedy clustering — assign each chunk to nearest cluster
       if similarity > threshold, else start new cluster
    4. Pick best chunk from each cluster
    """

    SIMILARITY_THRESHOLD = 0.82  # chunks above this are "same topic"

    def __init__(self):
        self.embedder = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )

    async def cluster_and_select(
        self,
        chunks: list[RetrievedChunk],
        max_clusters: int = 5,
    ) -> list[RetrievedChunk]:
        """
        Cluster case chunks and return one representative per cluster.
        Returns at most max_clusters chunks.
        """
        if len(chunks) <= 3:
            # no point clustering if very few chunks
            return chunks

        logger.info(f"Clustering {len(chunks)} case chunks")

        # embed all chunks
        texts = [c.text[:1000] for c in chunks]
        embeddings = await self.embedder.aembed_documents(texts)
        emb_matrix = np.array(embeddings)

        # cosine similarity matrix
        sim_matrix = cosine_similarity(emb_matrix)

        # greedy clustering
        clusters: list[list[int]] = []
        assigned = [False] * len(chunks)

        for i in range(len(chunks)):
            if assigned[i]:
                continue

            cluster = [i]
            assigned[i] = True

            for j in range(i + 1, len(chunks)):
                if assigned[j]:
                    continue
                if sim_matrix[i][j] >= self.SIMILARITY_THRESHOLD:
                    cluster.append(j)
                    assigned[j] = True

            clusters.append(cluster)

        logger.info(f"Formed {len(clusters)} clusters from {len(chunks)} chunks")

        # pick best (highest score) from each cluster
        representatives = []
        for cluster in clusters[:max_clusters]:
            best_idx = max(cluster, key=lambda i: chunks[i].score)
            representatives.append(chunks[best_idx])

        # sort by score descending
        representatives.sort(key=lambda c: c.score, reverse=True)

        logger.info(f"Selected {len(representatives)} representative chunks")
        return representatives