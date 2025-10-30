"""ingestion.py

Provide a small ingestion helper that evaluates a public Hugging Face model
against the project's Phase 1 metrics and returns whether it is ingestible.

Contract
--------
- ingestion(model: str) -> dict
  - Accepts a HuggingFace model id (owner/name) or a URL containing it.
  - Runs the rate-like metrics (non-latency scores) and returns a report
	containing each metric score, latencies, errors, and an "ingestible" flag.

If the package is ingestible (every non-latency score >= 0.5) the function
will call `upload_package(...)` which is a stub that can be replaced by a
real uploader later.
"""

from typing import Any, Dict, Tuple
import time
import requests
import logger

from metrics import (
	bus_factor,
	code_quality,
	ramp_up_time,
	data_quality,
	license as license_mod,
	reproducibility,
	reviewedness,
	performance_claims,
	dataset_and_code_score,
	size as size_mod,
)


def _extract_model_id(model: str) -> str:
	"""Normalize model identifier from URL or plain id."""
	if not model:
		return ""
	model = model.strip()
	# If it's a full URL, try to extract the path portion containing owner/name
	try:
		from urllib.parse import urlparse

		parsed = urlparse(model)
		path = parsed.path.strip("/")
		if path:
			parts = path.split("/")
			# If it contains 'tree' or 'blob' trim at that point
			if "tree" in parts:
				tree_index = parts.index("tree")
				return "/".join(parts[:tree_index])
			return path
	except Exception:
		pass
	return model

def ingestion(model: str) -> Dict[str, Any]:
	"""Evaluate a model and decide if it is ingestible.

	Returns a report dict with metric scores, latencies, errors and
	an 'ingestible' boolean.
	"""
	start_all = time.time()
	report: Dict[str, Any] = {
		"model": model,
		"metrics": {},
		"errors": [],
		"ingestible": False,
		"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
	}

	model_id = _extract_model_id(model)
	if not model_id:
		report["errors"].append("empty model id")
		return report

	# Fetch model info from HF API (best-effort)
	model_info: Dict[str, Any] = {}
	try:
		api_url = f"https://huggingface.co/api/models/{model_id}"
		resp = requests.get(api_url, timeout=10)
		if resp.status_code == 200:
			model_info = resp.json()
	except Exception as e:
		report["errors"].append(f"model_info_fetch_error: {e}")

	# Fetch README (best-effort)
	readme_text = ""
	try:
		raw_url = f"https://huggingface.co/{model_id}/raw/main/README.md"
		r = requests.get(raw_url, timeout=10)
		if r.status_code == 200:
			readme_text = r.text.lower()
	except Exception:
		pass

	# Prepare minimal placeholders for code/dataset info used by some metrics
	code_info: Dict[str, Any] = {}
	code_readme: str = ""
	code_url = ""
	dataset_url = ""

	# Metrics to run: mapping name -> callable
	metric_calls = {
		"bus_factor": lambda: bus_factor.bus_factor(model_info),
		"code_quality": lambda: code_quality.code_quality(model_info, code_info, readme_text, code_readme),
		"ramp_up_time": lambda: ramp_up_time.ramp_up_time(model_info),
		"data_quality": lambda: data_quality.data_quality(model_info, readme_text),
		"license": lambda: license_mod.get_license_score_cached(model_id),
		"reproducibility": lambda: reproducibility.reproducibility(model_info, code_info, readme_text),
		"reviewedness": lambda: reviewedness.reviewedness(code_info),
		"performance_claims": lambda: performance_claims.performance_claims(f"https://huggingface.co/{model_id}"),
		"dataset_and_code_score": lambda: dataset_and_code_score.dataset_and_code_score(code_url, dataset_url),
		"size": lambda: size_mod.calculate_size_score(model_id),
	}

	# Execute metrics and normalize outputs to (score, latency_ms)
	for name, fn in metric_calls.items():
		try:
			out = fn()
			if name == "size":
				# size returns (scores_dict, net_score, latency)
				if isinstance(out, tuple) and len(out) >= 2:
					if isinstance(out[1], (int, float)):
						score = float(out[1])
					else:
						score = 0.0
					latency = float(out[-1]) if len(out) >= 3 else 0.0
				else:
					score = 0.0
					latency = 0.0
			else:
				# expect (score, latency) or score only
				if isinstance(out, tuple):
					score = float(out[0])
					latency = float(out[1]) if len(out) > 1 else 0.0
				else:
					score = float(out)
					latency = 0.0

			report["metrics"][name] = {"score": round(score, 4), "latency_ms": round(latency, 2)}
		except Exception as e:
			report["metrics"][name] = {"score": 0.0, "latency_ms": 0}
			report["errors"].append(f"{name}_error: {e}")

	# Decide ingestibility: all non-latency metric scores >= 0.5
	non_latency_scores = [m["score"] for m in report["metrics"].values()]
	if non_latency_scores and all((s >= 0.5 or s == -1) for s in non_latency_scores):
		report["ingestible"] = True
	else:
		report["ingestible"] = False

	report["total_latency_ms"] = int((time.time() - start_all) * 1000)
	return report


if __name__ == "__main__":
	import sys

	if len(sys.argv) < 2:
		print("Usage: python ingestion.py <model-id-or-url>")
		sys.exit(2)

	result = ingestion(sys.argv[1])
	print(result)


