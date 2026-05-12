FROM flaresolverr/flaresolverr:latest

USER root
RUN apt-get update && apt-get install -y x11vnc && rm -rf /var/lib/apt/lists/*
USER flaresolverr
