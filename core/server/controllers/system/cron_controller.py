from typing import List
from fastapi import HTTPException
from core.registry import Registry
from core.scheduler.cron_manager import get_cron_manager
from apscheduler.schedulers.base import STATE_PAUSED, STATE_RUNNING
from core.server.controllers.base_controller import BaseController
from core.server.models.api_models import CronJobResponse, CronJobRequest

class CronController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.cron_manager = get_cron_manager()
        self.router.post("/cron/pause", status_code=204)(self.pause)
        self.router.post("/cron/resume", status_code=204)(self.resume)
        self.router.post("/cron/jobs", response_model=str)(self.add_job)
        self.router.delete("/cron/jobs/{job_id}", response_model=bool)(self.remove_job)
        self.router.get("/cron/jobs", response_model=List[CronJobResponse])(self.get_jobs)

    def pause(self) -> None:
        try:
            self.cron_manager.pause()
        except Exception as e:
            self.logger.error(f"Failed to pause cron: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to pause cron: {str(e)}")

    def resume(self) -> None:
        try:
            self.cron_manager.resume()
        except Exception as e:
            self.logger.error(f"Failed to resume cron: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to resume cron: {str(e)}")

    def add_job(self, job_in: CronJobRequest) -> str:
        try:
            func = Registry.get_target(job_in.func)
            func_kwargs = job_in.kwargs or {}

            return self.cron_manager.add_job(
                func=func,
                name=job_in.name,
                minute=job_in.minute,
                hour=job_in.hour,
                day=job_in.day,
                month=job_in.month,
                day_of_week=job_in.day_of_week,
                **func_kwargs
            )
        except RuntimeError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to add cron job: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to add cron job: {str(e)}")

    def remove_job(self, job_id: str) -> bool:
        try:
            return self.cron_manager.remove_job(job_id)
        except RuntimeError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to remove cron job {job_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to remove cron job: {str(e)}")

    def get_jobs(self) -> List[CronJobResponse]:
        try:
            jobs = []
            scheduler = self.cron_manager.scheduler
            for job in scheduler.get_jobs():
                jobs.append(CronJobResponse(
                    id=job.id,
                    name=job.name,
                    next_run_time=job.next_run_time,
                    trigger=str(job.trigger)
                ))
            return jobs
        except Exception as e:
            self.logger.error(f"Failed to list cron jobs: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to list cron jobs: {str(e)}")
