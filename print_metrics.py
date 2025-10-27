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
    reproducibility_score: float,
    reproducibility_latency: int,
    reviewedness_score: float,
    reviewedness_latency: int,
    treescore_score: float,
    treescore_latency: int,
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
        "net_score": round(net_score,2),
        "net_score_latency": int(net_score_latency),
        "ramp_up_time": round(ramp_up_time_score, 2),
        "ramp_up_time_latency": int(ramp_up_time_latency),
        "bus_factor": round(bus_factor_score, 2),
        "bus_factor_latency": int(bus_factor_latency),
        "performance_claims": round(performance_claims_score, 2),
        "performance_claims_latency": int(performance_claims_latency),
        "license": round(license_score, 2),
        "license_latency": int(license_latency),
        "size_score": size_score,  
        "size_score_latency": int(size_latency),
        "dataset_and_code_score": round(available_dataset_and_code_score, 2),
        "dataset_and_code_score_latency": int(available_dataset_and_code_latency),
        "dataset_quality": round(dataset_quality_score, 2),
        "dataset_quality_latency": int(dataset_quality_latency),
        "code_quality": round(code_quality_score, 2),
        "code_quality_latency": int(code_quality_latency),
        "reproducibility": round(reproducibility_score, 2),
        "reproducibility_latency": int(reproducibility_latency),
        "reviewedness": round(reviewedness_score, 2),
        "reviewedness_latency": int(reviewedness_latency),
        "treescore": round(treescore_score, 2),
        "treescore_latency": int(treescore_latency),
    }

    print(json.dumps(result,separators=(',' ':')))    



