from pydantic import BaseModel
import typing as t


class NodeOutputs(BaseModel):
    recommendations: t.List[t.Dict[str, str]]


class Inputs(BaseModel):
    description: t.Optional[str]
