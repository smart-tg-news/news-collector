import asyncio
from dotenv import load_dotenv

from scheduler.app import run_scheduler
from db.client import MongoClientSingleton


def setup() -> None:
    load_dotenv()
    MongoClientSingleton.init()

def exit() -> None:
    MongoClientSingleton.close()
    

if __name__ == "__main__":
    try:
        setup()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(run_scheduler())
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler stopped")
    finally:
        exit()