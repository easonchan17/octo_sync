from fastapi import HTTPException, Body
from typing import Optional, Dict, Any
from core.server.services.site_service import SiteService
from core.server.models.api_models import SiteRequest, SiteResponse
from core.server.controllers.base_controller import BaseController

class SiteController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.site_service = SiteService.get_instance()
        self.router.post("/sites", response_model=SiteResponse, status_code=201)(self.add_site)
        self.router.get("/sites/{site_name}", response_model=SiteResponse)(self.get_site)
        self.router.post("/sites/{site_name}/syncs/{resource}", response_model=str)(self.start_sync)
        self.router.delete("/sites/{site_name}/syncs/{resource}", response_model=str)(self.stop_sync)

    def get_site(self, site_name: str) -> SiteResponse:
        try:
            return self.site_service.get_site(site_name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to get site {site_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get site: {str(e)}")

    def add_site(self, site_in: SiteRequest) -> SiteResponse:
        try:
            return self.site_service.create_site(site_in.name, str(site_in.url))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to create site: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create site: {str(e)}")

    def start_sync(self, site_name: str, resource: str, payload: Optional[Dict[str, Any]] = Body(default=None)) -> str:
        try:
            return self.site_service.start_sync(site_name, resource, payload)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to start sync for site {site_name}, resource {resource}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to start sync: {str(e)}")

    def stop_sync(self, site_name: str, resource: str) -> str:
        try:
            return self.site_service.stop_sync(site_name, resource)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to stop sync for site {site_name}, resource {resource}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to stop sync: {str(e)}")