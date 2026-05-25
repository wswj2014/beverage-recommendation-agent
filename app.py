import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fastapi import FastAPI
from pydantic import BaseModel
from src.agent import BeverageRecommendAgent


app = FastAPI(title="Beverage Recommendation Agent")
agents: dict = {}


class ChatRequest(BaseModel):
    user_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    agent = agents.get(req.user_id)
    if agent is None:
        agent = BeverageRecommendAgent()
        agents[req.user_id] = agent
    reply = agent.run(req.message)
    return ChatResponse(reply=reply)


@app.post("/chat/{user_id}/clear")
def clear_chat(user_id: str):
    agent = agents.get(user_id)
    if agent:
        agent.clear()
    return {"status": "cleared"}
