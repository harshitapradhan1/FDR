from fastapi import APIRouter
from backend.app.evaluation.harness import run_evaluation_harness, get_latest_benchmark

router = APIRouter(prefix="/evaluation", tags=["Evaluation Harness & Benchmarks"])

@router.get("/latest")
def get_evaluation_metrics():
    """
    Returns empirical evaluation metrics (Precision, Recall, F1, Latency)
    measured on the labelled synthetic dataset.
    """
    return get_latest_benchmark()

@router.post("/run")
def trigger_evaluation_run():
    """
    Triggers a live run of the evaluation harness across synthetic test cases.
    """
    return run_evaluation_harness()

