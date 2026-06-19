# Edenseek Scout

Edenseek Scout is an always-on AI research agent developed by Edenseek Publishing.

Scout continuously monitors developments across:

* Artificial Intelligence
* Publishing
* Comics
* Digital Media
* Strategic opportunities relevant to Edenseek

The system generates autonomous intelligence reports, maintains persistent memory, and delivers research insights through a web dashboard.

## Current Status

Version: v0.3 Production Alpha

Deployment:

* Oracle Cloud VM
* FastAPI
* APScheduler
* Cloudflare DNS and HTTPS
* GitHub-based deployment workflow
* Persistent storage and memory

Production URL:

https://scout.edenseek.com/dashboard

## Architecture

Browser
↓
Cloudflare
↓
Nginx
↓
FastAPI
↓
Scout Agent
↓
OpenAI API

## Roadmap

### v0.4

* Structured memory extraction
* Knowledge accumulation
* Memory dashboard
* Security hardening
* Reliability improvements

### Future

* Active web research
* Conversational interface
* Reflection agent
* Critic agent
* Multi-agent orchestration

## Documentation

* docs/architecture/scout_v0.3_synopsis.md
* docs/architecture/scout_status_and_tech_debt.md
* docs/architecture/scout_beta_roadmap.md
* docs/architecture/scout_future_vision.md

## Mission

Scout's long-term objective is to become Edenseek's autonomous intelligence and research system, transforming accumulated knowledge into strategic guidance for publishing, AI, and creative projects.
