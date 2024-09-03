from typing import Dict

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class InputData(BaseModel):
    input: str

@app.post("/api/process")
async def process_input(data: InputData):
    user_input = data.input
    # Echo the input with "Bot: " prefix
    bot_response = f"Bot: {user_input}"
    return {"response": bot_response}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
