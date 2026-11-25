import multiprocessing
import os

bind = '0.0.0.0:8000'
workers = int(os.environ.get('WEB_CONCURRENCY', multiprocessing.cpu_count() * 2 + 1))
threads = 2
timeout = 30
graceful_timeout = 30
max_requests = 1000
max_requests_jitter = 100
worker_tmp_dir = '/dev/shm'
accesslog = '-'
errorlog = '-'