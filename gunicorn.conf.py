import multiprocessing

bind = "unix:cygnum.sock"
umask = 0o007

backlog = 2048

workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2