import chromadb


class MemoryRAG:

    def __init__(self):

        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(
            name="memories"
        )

        self._load_demo_memories()

    # ---------------------------------
    # Demo memories
    # ---------------------------------

    def _load_demo_memories(self):

        memories = [

            {
                "id": "1",
                "user_id": "rahul_singh",
                "text": "Rahul Singh is your grandson"
            },

            {
                "id": "2",
                "user_id": "rahul_singh",
                "text": "Rahul studies in Bangalore"
            },

            {
                "id": "3",
                "user_id": "ananya",
                "text": "Ananya is your daughter"
            }

        ]

        for m in memories:
            self.collection.add(
                documents=[m["text"]],
                ids=[m["id"]],
                metadatas=[{"user_id": m["user_id"]}]
            )

    # ---------------------------------
    # Query RAG
    # ---------------------------------

    def answer_query(self, user_id, question):

        results = self.collection.query(
            query_texts=[question],
            where={"user_id": user_id},
            n_results=3
        )

        memories = results["documents"][0]

        context = "\n".join(memories)

        prompt = f"""
The patient has Alzheimer's.

The person speaking is: {user_id}

Known memories:
{context}

Patient asked:
{question}

Respond clearly and simply.
"""

        # For demo we simulate an LLM response
        response = f"This is {user_id.replace('_',' ').title()}."

        return response
