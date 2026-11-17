# MLOps, CI/CD and monitoring

## What CI/CD is

Continuous integration and continuous deployment. An automated assembly line:
every time the code changes, it is tested, packaged and rolled out, with a way
back if something fails.

Moving software by hand is slow and somebody always forgets a step. CI/CD is
the discipline of never doing it by hand again.

## Monitoring

Once it is live, something has to watch whether it is up, fast and free of
errors, and raise an alarm at three in the morning so a human does not have to
sit staring at a screen.

## Where a trained model fits

Data is gathered and cleaned. A model is trained on it, occasionally, not on
every request. The trained model is saved as a file, an artifact. That file is
put behind an API so the rest of the app can send it a question.

Then it is monitored, because a model that was accurate last year goes quietly
stale as the world changes around it.
