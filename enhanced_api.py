# from version_info import get_version_info

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Milvus


from pymilvus import connections
import requests
import uvicorn
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse  # 修改导入
import logging
from datetime import datetime
import os


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)