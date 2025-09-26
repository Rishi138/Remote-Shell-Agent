from fastapi import FastAPI
from pydantic import BaseModel
import subprocess
import platform

app = FastAPI()


class Command(BaseModel):
    data: str


@app.post("/command")
async def command(data: Command):
    comm = data.data
    if platform.system() == "Windows":
        comm = 'cmd /c "{}"'.format(comm)
    try:
        result = subprocess.check_output(comm, shell=True, text=True)
        return {"data": result}
    except subprocess.CalledProcessError as e:
        return {"data": f"Error: {e.output or str(e)}"}
