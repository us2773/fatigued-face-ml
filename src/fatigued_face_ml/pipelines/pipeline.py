from kedro.pipeline import Node, Pipeline


from .nodes import (
    run_OpenFace,
    get_OpenFace_result,
    csv_to_dataframe,
    get_OpenFace_result,
    json_analyze,
    create_dataset,
    preview_feature_dataset,
    learning_model,
    leave_one_out_evaluate
)


def feature_extraction(**kwargs) -> Pipeline:
    return Pipeline(
        [
            Node(
                func=run_OpenFace,
                inputs=None,
                outputs="openface_extraction_log",
                name="run_OpenFace",
            ),
            Node(
                func=get_OpenFace_result,
                inputs=None,
                outputs="openface_csv",
                name="get_OpenFace_result",
            )
        ])
    
def create_dataset_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            Node(
                func=get_OpenFace_result,
                inputs=None,
                outputs="openface_csv",
                name="get_OpenFace_result",
            ),
            Node(
                func=csv_to_dataframe,
                inputs="openface_csv",
                outputs="cleaned_dataframe",
                name="csv_to_dataframe",
            ),
            Node(
                func=json_analyze,
                inputs="raw_json",
                outputs="metadata_map",
                name="json_analyze",
            )
            ,Node(
                func=create_dataset,
                inputs=["cleaned_dataframe", "metadata_map"],
                outputs="feature_dataset",
                name="create_dataset",
            ),
            Node(
            func=preview_feature_dataset,
            inputs="feature_dataset",
            outputs="feature_dataset_preview",
            name="preview_feature_dataset",
)
        ])
    
def machine_learning(**kargs) -> Pipeline:
    return Pipeline(
        [
            Node(
                func=learning_model,
                inputs=["feature_dataset", "params:param.vas_num", "params:param.name", "params:param.features"],
                outputs="fatigue_model",
                name="learning_model"
            ),
            Node(
                func=leave_one_out_evaluate,
                inputs=["feature_dataset", "params:param.vas_num", "params:param.name", "params:param.features"],
                outputs="report_scores",
                name="leave_one_out_evaluate"
            )
        ]
    )