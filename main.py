import asyncio

from scheduler.app import run_scheduler

if __name__ == "__main__":
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(run_scheduler())
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler stopped")