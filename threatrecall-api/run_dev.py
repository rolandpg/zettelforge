import os

# Set environment to use env provider for dev
os.environ["TR_SECRETS_BACKEND"] = "env"

from threatrecall_api.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
