from core.store.postgres.daos.common import SysValDao

class ModuleConfig:
    def __init__(self, module: str) -> None:
        self.module = module
        self._dao = SysValDao()

    def load(self) -> None:
        vals = self._dao.get_vals(self.module)
        if not vals:
            return

        for key, val in vals.items():
            setattr(self, key, val)