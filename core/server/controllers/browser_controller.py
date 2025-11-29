from fastapi import HTTPException
from core.server.controllers.base_controller import BaseController
from core.server.services.browser_service import BrowserService
from core.server.models.browser_models import PagePoolStatus

class BrowserController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.browser_service = BrowserService()
        self.router.get("/browser/page-pool/status")(self.get_page_pool_status)

    async def get_page_pool_status(self) -> PagePoolStatus:
        try:
            return self.browser_service.get_page_pool_status()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to get page pool status: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get page pool status: {str(e)}")