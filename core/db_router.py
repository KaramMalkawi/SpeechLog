class ReadReplicaRouter:
    """Route read queries to the replica when configured."""

    def db_for_read(self, model, **hints):
        if "replica" in hints.get("databases", {}):
            return "replica"
        return "replica" if self._has_replica() else "default"

    def db_for_write(self, model, **hints):
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == "default"

    @staticmethod
    def _has_replica() -> bool:
        from django.conf import settings

        return "replica" in settings.DATABASES
