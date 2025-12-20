from core.browser.interceptor import Interceptor
from core.server.services.base_service import BaseService
from core.server.models.browser_models import PagePoolStatus

class BrowserService(BaseService):

    def get_page_pool_status(self) -> PagePoolStatus:
        page_pool = Interceptor.get_instance().get_page_pool()

        if not page_pool:
            raise ValueError("Page pool is not initialized")

        return PagePoolStatus(
            capacity=page_pool.get_capacity(),
            count=page_pool.get_count(),
        )