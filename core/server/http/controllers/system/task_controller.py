from fastapi import HTTPException, Body
from typing import Optional, Dict, Any
from core.services.task_service import TaskService
from core.server.http.controllers.base_controller import BaseController

class TaskController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.task_service = TaskService.get_instance()
        self.router.post("/tasks/{action}/{site_name}/{resource}", response_model=str)(self.start_task)
        self.router.delete("/tasks/{action}/{site_name}/{resource}", response_model=str)(self.stop_task)

    def start_task(self, action: str, site_name: str, resource: str, payload: Optional[Dict[str, Any]] = Body(default=None)) -> str:
        try:
            return self.task_service.start_task(action, site_name, resource, payload)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to start task for site {site_name}, resource {resource}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to start task: {str(e)}")

    def stop_task(self, action: str, site_name: str, resource: str) -> str:
        try:
            return self.task_service.stop_task(action, site_name, resource)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to stop task {action}.{site_name}.{resource}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to stop task: {str(e)}")
