import uvicorn

from fastapi import FastAPI
from src.backend import vacancies
from src.backend.config import Config
from src.backend.constants import PROJECT_PATH


def main() -> FastAPI:
    app = FastAPI()
    config = Config.from_yaml(path=PROJECT_PATH / 'config.yaml')

    container = vacancies.Container()
    container.config.from_dict(options=config)
    container.wire(modules=[vacancies.routes])

    app.include_router(router=vacancies.router)

    return app


if __name__ == '__main__':
    app = main()
    uvicorn.run(app, host='0.0.0.0', port=8000)
