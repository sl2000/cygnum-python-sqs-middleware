import multiprocessing

bind = "unix:cygnum.sock"
umask = 0o007

backlog = 2048

# workers = multiprocessing.cpu_count() * 2 + 1
workers = 1
threads = 2
worker_class = 'eventlet'
worker_connections = 100

max_requests = 1000 # This is a simple method to help limit the damage of memory leaks.
max_requests_jitter = 50

graceful_timeout = 120 # After receiving a restart signal, workers have this much time to finish serving requests. Workers still alive after the timeout (starting from the receipt of the restart signal) are force killed.

timeout = 30 # Workers silent for more than this many seconds are killed and restarted.
keepalive = 2
