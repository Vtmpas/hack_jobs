from omegaconf import OmegaConf
from pydantic import BaseModel


class RecSysConfig(BaseModel):
    vector_encoder: str
    reranker: str


class Config(BaseModel):
    recsys: RecSysConfig

    @classmethod
    def from_yaml(cls, path: str) -> 'Config':
        cfg = OmegaConf.to_container(OmegaConf.load(path), resolve=True)
        return cls(**cfg)
