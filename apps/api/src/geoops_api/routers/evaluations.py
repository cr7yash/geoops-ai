"""Persisted evaluation runs and measured aggregate metrics."""

from fastapi import APIRouter, HTTPException, Request

from geoops_api.container import ApplicationContainer
from geoops_api.evaluation import EvaluationRun

router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])


@router.get("", response_model=list[EvaluationRun])
async def list_runs(request: Request) -> list[EvaluationRun]:
    container: ApplicationContainer = request.app.state.container
    return await container.evaluation_service.list_runs()


@router.get("/{run_id}", response_model=EvaluationRun)
async def get_run(run_id: str, request: Request) -> EvaluationRun:
    container: ApplicationContainer = request.app.state.container
    document = await container.approval_repository.store.get(f"evaluations/{run_id}")
    if document is None:
        raise HTTPException(404, "Evaluation run not found")
    return EvaluationRun.model_validate(document)


@router.post("/run", response_model=EvaluationRun)
async def run_evaluation(request: Request) -> EvaluationRun:
    container: ApplicationContainer = request.app.state.container
    return await container.evaluation_service.run()
