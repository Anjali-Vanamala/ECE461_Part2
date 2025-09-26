import json

def print_model_evaluation(
    api_info: dict, 
    size_score: dict,
    size_latency: int, 
    license_score: float, 
    license_latency: int,
    ramp_up_time_score: float, 
    ramp_up_time_latency: int, 
    bus_factor_score: float, 
    bus_factor_latency: int, 
    available_dataset_and_code_score: float, 
    available_dataset_and_code_latency: int, 
    dataset_quality_score: float, 
    dataset_quality_latency: int, 
    code_quality_score: float, 
    code_quality_latency: int, 
    performance_claims_score: float, 
    performance_claims_latency: int, 
    net_score: float,
    net_score_latency: int
): 
    """
    Print a JSON-formatted dictionary summarizing the evaluation of a model.

    Parameters
    ----------
    api_info : dict
        Dictionary containing API metadata. Expected to have an 'id' field in the format 'namespace/model_name'.
    size_score : dict
        Dictionary representing the size evaluation of the model (e.g., {"value": float, "unit": str}).
    size_latency : int
        Latency in milliseconds associated with the size score evaluation.
    license_score : float
        Score representing the permissiveness or compatibility of the API's license.
    license_latency : int
        Latency in milliseconds associated with evaluating the license.
    ramp_up_time_score : float
        Score representing how quickly a developer can become productive with the API.
    ramp_up_time_latency : int
        Latency in milliseconds associated with evaluating ramp-up time.
    bus_factor_score : float
        Score representing the risk associated with knowledge concentration (bus factor) in the API's ecosystem.
    bus_factor_latency : int
        Latency in milliseconds associated with evaluating bus factor.
    available_dataset_and_code_score : float
        Score reflecting availability of datasets and example code for the API.
    available_dataset_and_code_latency : int
        Latency in milliseconds associated with evaluating dataset and code availability.
    dataset_quality_score : float
        Score reflecting the quality of datasets available for the API.
    dataset_quality_latency : int
        Latency in milliseconds associated with evaluating dataset quality.
    code_quality_score : float
        Score representing the quality of available code for the API.
    code_quality_latency : int
        Latency in milliseconds associated with evaluating code quality.
    performance_claims_score : float
        Score assessing the validity or credibility of performance claims made by the API.
    performance_claims_latency : int
        Latency in milliseconds associated with evaluating performance claims.
    net_score : float
        Overall aggregated score for the API.
    net_score_latency : int
        Latency in milliseconds associated with calculating the net score.

    Returns
    -------
    None
        Prints the JSON-formatted evaluation dictionary to stdout.
    """
    
    name = api_info.get("id").split('/')[1]
    category = "MODEL"

    result = {
        "name": name,
        "category": category,
        "net_score": net_score,
        "net_score_latency": net_score_latency,
        "ramp_up_time": ramp_up_time_score,
        "ramp_up_time_latency": ramp_up_time_latency,
        "bus_factor": bus_factor_score,
        "bus_factor_latency": bus_factor_latency,
        "performance_claims": performance_claims_score,
        "performance_claims_latency": performance_claims_latency,
        "license": license_score,
        "license_latency": license_latency,
        "size_score": size_score,  
        "size_score_latency": size_latency,
        "dataset_and_code_score": available_dataset_and_code_score,
        "dataset_and_code_score_latency": available_dataset_and_code_latency,
        "dataset_quality": dataset_quality_score,
        "dataset_quality_latency": dataset_quality_latency,
        "code_quality": code_quality_score,
        "code_quality_latency": code_quality_latency,
    }

    print(json.dumps(result))    



