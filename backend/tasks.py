"""Single worker owns every GPU operation. Queue metadata survives restarts."""

from queue import Queue
from threading import Thread
from .storage import now


class Cancelled(Exception):
    pass


class Tasks:
    def __init__(self, store):
        self.store = store
        self.queue = Queue()
        self.closed = False
        with store.lock:
            for task in store.list("tasks"):
                if task["status"] in {"queued", "running"}:
                    task.update(
                        status="interrupted", message="服务重启，任务未自动重试"
                    )
                    store.save("tasks", task)
        self.worker = Thread(target=self._run, daemon=True, name="webui3-inference")
        self.worker.start()

    def submit(self, kind, function, session_ids=None, audio_ids=None):
        with self.store.lock:
            if self.closed:
                raise ValueError("服务正在停止")
            task = self.store.create(
                "tasks",
                {
                    "kind": kind,
                    "status": "queued",
                    "progress": 0,
                    "message": "等待执行",
                    "session_ids": session_ids or [],
                    "result": None,
                    "error": None,
                    "cancel_requested": False,
                    "audio_ids": audio_ids or [],
                },
            )
            self.queue.put((task["id"], function))
            return task

    def busy(self, session_ids):
        return any(
            t["status"] in {"queued", "running"}
            and set(t["session_ids"]) & set(session_ids)
            for t in self.store.list("tasks")
        )

    def cancel(self, key):
        with self.store.lock:
            task = self.store.get("tasks", key)
            if task["status"] in {"queued", "running"}:
                task["cancel_requested"] = True
                if task["status"] == "queued":
                    task["status"] = "cancelled"
                task["message"] = "取消已请求，等待安全边界"
                self.store.save("tasks", task)
            return task

    def progress(self, key, value=None, desc="", **kwargs):
        with self.store.lock:
            task = self.store.get("tasks", key)
            if task["cancel_requested"]:
                raise Cancelled()
            if value is not None:
                task["progress"] = min(1, max(0, float(value)))
            task["message"] = desc
            self.store.save("tasks", task)

    def _run(self):
        while True:
            item = self.queue.get()
            if item is None:
                return
            key, function = item
            try:
                with self.store.lock:
                    task = self.store.get("tasks", key)
                    if task["cancel_requested"]:
                        continue
                    task.update(status="running", started_at=now())
                    self.store.save("tasks", task)
                result = function(
                    lambda value=None, desc="", **kw: self.progress(
                        key, value, desc, **kw
                    )
                )
                self.progress(key, 1, "完成")
                self._finish(key, "succeeded", result=result)
            except Cancelled:
                self._finish(key, "cancelled", message="已取消")
            except Exception as error:
                self._finish(key, "failed", error=str(error), message=str(error))
            finally:
                self.queue.task_done()

    def _finish(self, key, status, **fields):
        with self.store.lock:
            task = self.store.get("tasks", key)
            task.update(status=status, finished_at=now(), **fields)
            self.store.save("tasks", task)

    def close(self):
        with self.store.lock:
            self.closed = True
            for task in self.store.list("tasks"):
                if task["status"] in {"queued", "running"}:
                    self.cancel(task["id"])
        self.queue.put(None)
        self.worker.join()
