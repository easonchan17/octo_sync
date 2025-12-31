from typing import Dict, Any, List, Optional
from fastapi import HTTPException, Body
from apscheduler.schedulers.base import STATE_PAUSED, STATE_RUNNING
from core.scheduler.cron import Cron
from core.registry import Registry
from core.server.controllers.base_controller import BaseController

class CronController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.cron = Cron.get_instance()
        self.router.post("/cron/pause")(self.pause)
        self.router.post("/cron/resume")(self.resume)
        self.router.get("/cron/status")(self.get_status)
        self.router.get("/cron/jobs")(self.list_jobs)
        self.router.post("/cron/jobs")(self.add_job)
        self.router.delete("/cron/jobs/{job_id}")(self.remove_job)

    def pause(self) -> Dict[str, str]:
        try:
            self.cron.pause()
            return {"status": "paused", "message": "Cron scheduler paused"}
        except Exception as e:
            self.logger.error(f"Failed to pause cron: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to pause cron: {str(e)}")

    def resume(self) -> Dict[str, str]:
        try:
            self.cron.resume()
            return {"status": "resumed", "message": "Cron scheduler resumed"}
        except Exception as e:
            self.logger.error(f"Failed to resume cron: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to resume cron: {str(e)}")

    def get_status(self) -> Dict[str, Any]:
        try:
            scheduler = self.cron.scheduler
            status = {
                "running": scheduler.running,
                "state": "running" if scheduler.state == STATE_RUNNING else "paused" if scheduler.state == STATE_PAUSED else "stopped",
                "job_count": len(scheduler.get_jobs())
            }
            return status
        except Exception as e:
            self.logger.error(f"Failed to get cron status: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get cron status: {str(e)}")

    def list_jobs(self) -> List[Dict[str, Any]]:
        try:
            scheduler = self.cron.scheduler
            jobs = []
            for job in scheduler.get_jobs():
                jobs.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger)
                })
            return jobs
        except Exception as e:
            self.logger.error(f"Failed to list cron jobs: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to list cron jobs: {str(e)}")

    def add_job(self, payload: Dict[str, Any] = Body(...)) -> Dict[str, str]:
        try:
            func_name = payload.get("func")
            name = payload.get("name")
            minute = payload.get("minute")
            hour = payload.get("hour")
            day = payload.get("day")
            month = payload.get("month")
            day_of_week = payload.get("day_of_week")
            func_kwargs = payload.get("kwargs", {})
            func = Registry.fetch(func_name)

            job_id = self.cron.add_job(
                func=func,
                name=name,
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                **func_kwargs
            )
            return {"job_id": job_id, "message": f"Job {job_id} added successfully"}
        except RuntimeError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to add cron job: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to add cron job: {str(e)}")

    def remove_job(self, job_id: str) -> Dict[str, str]:
        try:
            success = self.cron.remove_job(job_id)
            result = "successfully" if success else "unsuccessfully"
            return {"message": f"Job {job_id} removed {result}"}
        except RuntimeError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to remove cron job {job_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to remove cron job: {str(e)}")
