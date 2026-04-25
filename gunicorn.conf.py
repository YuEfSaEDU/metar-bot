workers = 1
bind = "0.0.0.0:" + os.environ.get("PORT", "10000")


def post_worker_init(worker):
    from app import start_bot_thread
    start_bot_thread()
