# run.py
import uvicorn

if __name__ == "__main__":
    # El mismo comando que usaste en Makefile, pero como argumentos
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)