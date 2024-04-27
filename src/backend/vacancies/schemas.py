from pydantic import BaseModel
import typing as t


class NodeOutputs(BaseModel):
    recommendations: t.List[t.Dict[str, str]]
