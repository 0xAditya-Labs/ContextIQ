from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from .config import settings

app = FastAPI(title="ContextIQ IT Support API")

# What is CORS and why is it needed?
# CORS (Cross-Origin Resource Sharing) is a security feature built into web browsers.
# By default, a browser running a React app on http://localhost:3000 will block any 
# API requests made to a backend running on a different port (like http://localhost:8000).
# The browser does this to prevent malicious websites from stealing your data in the background.
# 
# We add CORSMiddleware here to explicitly tell the browser: "It is perfectly safe to 
# allow requests from the React frontend to hit this backend API."
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace "*" with exact frontend URLs (e.g., ["http://localhost:3000"])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attach our endpoints from routes.py
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
