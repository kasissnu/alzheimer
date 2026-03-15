import chromadb


class MemoryRAG:

    def __init__(self):

        self.client = chromadb.Client()

        self.collection = self.client.get_or_create_collection(
            name="memories"
        )

        self.load_demo_memories()

    # -----------------------------
    # Load example memories
    # -----------------------------

    def load_demo_memories(self):

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
                "user_id": "rahul_singh",
                "text": "Rahul visited you yesterday"
            },

            {
                "id": "4",
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

    # -----------------------------
    # Query memories
    # -----------------------------

    def answer_query(self, user_id, question):

        results = self.collection.query(
            query_texts=[question],
            where={"user_id": user_id},
            n_results=3
        )

        memories = results["documents"][0]

        context = "\n".join(memories)

        print("\nRetrieved memories:")
        print(context)

        # Simulated response
        name = user_id.replace("_", " ").title()

        response = f"This is {name}. {memories[0]}."

        return response
