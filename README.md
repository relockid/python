Relock python SDK
=================

Relock introduces a groundbreaking approach to security through continuous passive authentication. This innovative technology works silently in the background, constantly validating the legitimacy of user sessions in real-time. By doing so, Relock effectively neutralizes the risks associated with both phishing attacks, where users are tricked into revealing credentials, and session hijacking, where attackers seize control of active user sessions.

Minimal example
---------------
Run service:

    docker pull relockid/sentinel
    docker run --privileged --network host -it relock/sentinel run \
           --host 127.0.0.1 --port 8111 \
           --multiprocessing

Python:

    python3 -m pip install relock
    
    from relock import Flask as relock

GitHub repository
-----------------

This repository contains ready-to-use, minimal implementation of the producer server and the consumer for test purpose of re:lock sentinel. This minimal implementation makes it easy to check how the system works in practice.

You can run the demo solution on one machine, as consumer and producer may use the same enclave for this purpose.

Links
-----

-   Docker: https://hub.docker.com/u/relockid
-   Documentation: https://relock.security/docs
-   Demo Source Code: https://github.com/relockid
-   Issue Tracker: https://github.com/relockid/sentinel/issues
-   Website: https://relock.security/