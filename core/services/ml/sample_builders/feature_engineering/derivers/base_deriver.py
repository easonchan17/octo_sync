from abc import abstractmethod
from ..context import FeatureContext

class BaseDeriver(FeatureContext):
    @abstractmethod
    def derive(self, *args, **kwargs) -> None:
        pass
