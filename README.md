# Datasheet Support Agent

Answers engineers' questions about Analog Devices parts from the public datasheets, citing the
datasheet page for every number, and refuses (with a pointer to EngineerZone) when the datasheet
doesn't say.

> Independent demo built on public datasheets. Not affiliated with or endorsed by Analog Devices.
> Datasheets are downloaded by a script and are not redistributed in this repository.

**Status:** Phase 0 of 7 (project skeleton). Retrieval, agent and evaluation results will be
added here as they are measured.

## Run

```bash
make up     # Postgres 16 + pgvector on port 5433
make test
```
