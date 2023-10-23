#!/usr/bin/sudo python
"""
Usage:
- Run app: poetry run python run.py
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "gen3discoveryai.main:app",
        host="0.0.0.0",
        port=8089,
        reload=True,
        log_config=None,
    )
