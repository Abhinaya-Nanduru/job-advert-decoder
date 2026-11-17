# Cloud platforms and deployment

## What the cloud actually is

Computers in someone else's building that you rent instead of buying. Your
backend and your database have to run somewhere that is always on and always
connected, and that cannot be your laptop.

AWS, Azure and GCP are the three large providers. Smaller platforms like
Render and Vercel sit on top of them and hide most of the detail.

## Deployment and environments

Deployment is the moment your code stops running on your machine and starts
running on one of those rented computers where real people can reach it.

Teams keep several copies of the same app. Development is where things break
safely. Staging is a rehearsal that looks like the real thing. Production is
what users depend on.

## Secrets

Secrets are the API keys and passwords the app needs. They live in the
environment's settings, never in the code. A key committed to a repository is
found by automated scrapers within minutes and spent on someone else's bill.

## Serverless, and why your database disappeared

Some platforms do not rent you a computer at all. They run your code for a few
seconds when a request arrives and then throw the container away.

That means anything written to a local file is gone. A database file that
works perfectly on your laptop will silently lose every row in production.
This is the most common surprise for people deploying their first service, and
it is why a hosted database exists.
