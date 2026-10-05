import argparse
import uvicorn

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7863)
    args = parser.parse_args()
    uvicorn.run(
        "backend.app:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        workers=1,
    )
