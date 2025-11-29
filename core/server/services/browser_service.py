from core.browser.interceptor import Interceptor
from core.server.services.base_service import BaseService
from core.server.models.browser_models import PagePoolStatus

class BrowserService(BaseService):

    def get_page_pool_status(self) -> PagePoolStatus:
        page_pool = Interceptor.get_instance().get_page_pool()

        if not page_pool:
            raise ValueError("Page pool is not initialized")

        return PagePoolStatus(
            total_created=page_pool.get_created_count(),
            available_in_pool=page_pool.get_available_count(),
            max_size=page_pool.get_max_size(),
            in_use=page_pool.get_created_count() - page_pool.get_available_count()
        )