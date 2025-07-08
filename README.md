Relock python SDK
=================

Relock is a high-frequency cryptographic key rotation server that authenticates each individual request using ephemeral, transient, key. This enables digital platforms to implement true continuous passive authentication.

By leveraging rapid, per-request key changes, Relock ensures every interaction is independently verified, boosting security posture while maintaining a seamless user experience. Server is designed to scale effortlessly, making it ideal for use cases that require both high performance and uncompromised trust.

Minimal example
---------------
Run service:

    docker pull relockid/server
    docker run --privileged --network host \
           -it relock/server run \
           --host 127.0.0.1 --port 8111 \
           --multiprocessing

Flask:

    python3 -m pip install relock
    
    from relock import Flask as relock

GitHub repository
-----------------

This repository contains ready-to-use, minimal implementation of the TCP client for Relock Server. This minimal implementation makes it easy to check how the system works in practice.

Links
-----

-   Docker: https://hub.docker.com/r/relockid
-   Documentation: https://docs.relock.id
-   Demo Source Code: https://github.com/relockid
-   Website: https://relock.security/