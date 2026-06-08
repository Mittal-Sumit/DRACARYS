import os
import sys
import threading

from django.apps import AppConfig


class ProposalAiConfig(AppConfig):
    name = "proposal_ai"

    def ready(self):
        import sys
        argv = sys.argv
        # Only pre-warm for actual server processes (runserver or gunicorn).
        # Management commands (migrate, collectstatic, shell, etc.) exit quickly
        # and kill the daemon thread mid-C++ operation, causing a core dump.
        is_management = argv and "manage.py" in argv[0]
        is_runserver = "runserver" in argv
        if is_management and not is_runserver:
            return
        # Spawn a daemon thread so model loading doesn't block Django startup.
        # Daemon=True means it won't prevent the process from exiting.
        threading.Thread(target=self._warm_models, daemon=True).start()

    @staticmethod
    def _warm_models():
        try:
            # rag/ and ingestion/ live at the project root, two levels above this file
            # (backend/proposal_ai/apps.py → backend/ → project root)
            root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if root not in sys.path:
                sys.path.insert(0, root)

            from rag.retriever import retrieve
            retrieve("warmup", n_results=1)
            print("[Dracarys] Models pre-warmed — embedding model + reranker ready.")
        except Exception as exc:
            # Never crash startup. ChromaDB may be empty on first run — that's fine.
            print(f"[Dracarys] Model pre-warm skipped: {exc}")
