from dependency_injector import containers, providers

from src.backend.vacancies.services import SearchCourses
from src.backend.config import Config


class Container(containers.DeclarativeContainer):
    config: Config = providers.Configuration()

    analyzer = providers.Singleton(
        SearchCourses,
        config=config.recsys
    )
