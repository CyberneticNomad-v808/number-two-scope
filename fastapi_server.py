from fastapi import FastAPI
import uvicorn
from typing import Dict

app = FastAPI(title="SpiderFoot API")

@app.get("/")
async def root() -> Dict[str, str]:
    return {"message": "Welcome to SpiderFoot API"}

@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy"}

@app.get("/info")
async def server_info() -> Dict[str, str]:
    return {
        "name": "SpiderFoot API",
        "version": "1.0.0",
        "description": "API for SpiderFoot operations"
    }

if __name__ == "__main__":
    print("Starting FastAPI web server at http://0.0.0.0:5001/")
    uvicorn.run(app, host="0.0.0.0", port=5001)
```
