from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from fastapi.responses import Response

from src.backend.vacancies.container import Container
from src.backend.vacancies.schemas import NodeOutputs

router = APIRouter(prefix='/vacancies', tags=['vacancies'])


@router.get('/health')
def health():
    return Response(content='OK')


@router.post(
    path='/recommend',
    response_model=NodeOutputs,
    description='Run models to get relevant course recommendations',
)
@inject
def predict(
        description: str,
        analyzer=Depends(Provide[Container.analyzer]),
) -> NodeOutputs:
    return NodeOutputs(big_string=analyzer.get_vacancies_by_desc(description))
