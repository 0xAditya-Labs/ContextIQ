import chromadb

class ChromaDBSingleton:
    _instance = None

    @classmethod
    def get_client(cls):
        # SINGLETON PATTERN: avoids re-initializing DB client on every call, 
        # which causes repeated disk I/O and slow cold-starts.
        if cls._instance is None:
            # We initialize the PersistentClient. 
            # Note: newer chromadb uses `path` rather than `persist_directory`.
            cls._instance = chromadb.PersistentClient(path="./chroma_db")
        return cls._instance
