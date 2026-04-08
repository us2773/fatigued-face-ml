"""Project pipelines."""
from __future__ import annotations

from kedro.pipeline import Pipeline
import fatigued_face_ml.pipelines.pipeline as pl


def register_pipelines() -> dict[str, Pipeline]:
    """Register the project's pipelines.

    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.
    """
    openface_exec = pl.feature_extraction()
    create_dataset_pipeline = pl.create_dataset_pipeline()
    machine_learning = pl.machine_learning()
    return {
        "__default__": create_dataset_pipeline + machine_learning,
        "feature_extraction": openface_exec,
            }

