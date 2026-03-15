
import chromadb

class MemoryRAG:

    def __init__(self):
        self.client=chromadb.Client()
        self.collection=self.client.get_or_create_collection(name="memories")
        self.load_demo_memories()

    def load_demo_memories(self):

        memories=[
        {"id":"1","user_id":"rahul_singh","text":"Rahul Singh is your grandson"},
        {"id":"2","user_id":"rahul_singh","text":"Rahul studies in Bangalore"},
        {"id":"3","user_id":"rahul_singh","text":"Rahul visited you yesterday"}
        ]

        for m in memories:
            self.collection.add(
            documents=[m["text"]],
            ids=[m["id"]],
            metadatas=[{"user_id":m["user_id"]}]
            )

    def answer_query(self,user_id,question):

        results=self.collection.query(
        query_texts=[question],
        where={"user_id":user_id},
        n_results=2
        )

        memories=results["documents"][0]

        if not memories:
            return "I do not know this person."

        name=user_id.replace("_"," ").title()

        return f"This is {name}. {memories[0]}."
