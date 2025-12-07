# import parse_categories
import json
from datetime import datetime, timedelta
from unittest import IsolatedAsyncioTestCase
from unittest.mock import MagicMock, mock_open, patch

import requests as rq

import input
import metrics.code_quality
import metrics.data_quality
from input import find_dataset, main
from metrics.bus_factor import bus_factor
from metrics.dataset_and_code_score import dataset_and_code_score
from metrics.license import (extract_license_section,
                             get_detailed_license_score, get_license_score,
                             get_license_score_cached)
from metrics.performance_claims import performance_claims
from metrics.ramp_up_time import ramp_up_time
from metrics.size import (SIZE_WEIGHTS, calculate_net_size_score,
                          calculate_size_score, calculate_size_score_cached,
                          calculate_size_scores, extract_model_id_from_url,
                          get_detailed_size_score, get_model_size_for_scoring)

"""
Usage Instructions:

Dependencies:
Install pytest in terminal: pip install pytest

Commands:
Run a certain test (ex: just test_add_1):           pytest test_example.py::Test_Add::test_add_1 -v
Run a certain class of tests (ex: just Test_Add):   pytest test_example.py::Test_Add -v
Run all the tests in the file:                      pytest test_example.py -v

Test Suite for Data Quality and Code Quality Functions

Disclaimer:
Test cases were developed with Claude Sonnet 4 assistance due to the complexity of manually
constructing realistic test data and calculating accurate scoring thresholds. Since our code
structure doesn't support passing in real URLs in a test suite, AI assistance was used to:
    1. Generate realistic API response structures mirroring HF and GitHub data
    2. Calculate expected scores based on weighted metrics in our quality functions
"""


class Test_Size_Score:
    def test_gpt2_size_score(self):
        """Test size calculation for GPT-2 model"""
        raw_model_url = "https://huggingface.co/gpt2"
        size_scores, net_size_score, size_latency = metrics.size.calculate_size_score(raw_model_url)
        # GPT-2 should use default 0.5GB
        expected_scores = {
            'raspberry_pi': 0.75,
            'jetson_nano': 0.88,
            'desktop_pc': 0.97,
            'aws_server': 1.0
        }
        for device, expected in expected_scores.items():
            assert abs(size_scores[device] - expected) < 0.02

    def test_ms_large_size_score(self):
        raw_model_url = "https://huggingface.co/microsoft/DialoGPT-large"
        size_scores, net_size_score, size_latency = metrics.size.calculate_size_score(raw_model_url)
        # T5-small should use default 0.5GB
        expected_scores = {
            'raspberry_pi': 0.75,
            'jetson_nano': 0.88,
            'desktop_pc': 0.97,
            'aws_server': 1.0
        }
        for device, expected in expected_scores.items():
            assert abs(size_scores[device] - expected) < 0.01


class Test_Dataset_Quality:  # Model tests
    def test_model_good(self):  # Good data quality case
        api_info = {
            'cardData': {
                'license': 'MIT',
                'description': 'Clear model description',
                'tags': ['nlp', 'classification'],
                'citation': 'Please cite our paper',
                'source': 'Original research data',
                'language': ['en', 'es'],
                'use': 'Text classification tasks',
                'limitation': 'May not work on domain-specific text'
            },
            'createdAt': (datetime.now() - timedelta(days=30)).isoformat() + 'Z'  # 30 days old = recent
        }
        # Perfect README with all keywords
        readme = """
        This model demonstrates diverse and varied approaches to text classification.
        The training data represents a comprehensive range of different text types.

        Our dataset is well-balanced and evenly distributed across multiple categories.
        The representative sample captures extensive coverage of the target domain.

        type: accuracy
        value: 0.95

        Additional keywords: heterogeneous, broad, spanning, proportional coverage
        with citation information, source attribution, and language specifications.
        Uses include various limitation scenarios with proper description.
        """
        # Unpack the tuple - get score and latency
        score, latency = metrics.data_quality.data_quality(api_info, readme)
        assert score >= 0.9  # Test only the score

    def test_dataset_poor(self):  # Poor data quality case
        api_info = {
            'cardData': {},
            'createdAt': (datetime.now() - timedelta(days=800)).isoformat() + 'Z'
        }
        readme = "Model."
        # Unpack the tuple
        score, latency = metrics.data_quality.data_quality(api_info, readme)
        assert score <= 0.3

    def test_dataset_good(self):  # Good data quality case
        api_info = {
            'cardData': {
                'license': 'MIT',
                'description': 'Comprehensive dataset description',
                'tags': ['dataset', 'nlp'],
                'citation': 'Please cite our dataset',
                'source': 'Academic research',
                'language': ['en'],
                'use': 'Text classification',
                'limitation': 'Limited to English text'
            },
            'createdAt': (datetime.now() - timedelta(days=60)).isoformat() + 'Z'
        }

        readme = """
        This dataset contains diverse and representative samples from various sources.
        The data is well-balanced across different categories and comprehensive in scope.
        type: accuracy
        value: 0.92
        """
        # Unpack the tuple
        score, latency = metrics.data_quality.data_quality(api_info, readme)
        assert score >= 0.8

    def test_dataset_bad(self):  # Poor data quality case
        api_info = {
            'cardData': {},
            'createdAt': (datetime.now() - timedelta(days=900)).isoformat() + 'Z'
        }
        readme = "Old dataset with minimal info."
        # Unpack the tuple
        score, latency = metrics.data_quality.data_quality(api_info, readme)
        assert score <= 0.3


class Test_Code_Quality:  # Github repo tests
    def test_code_good(self):  # Good code quality case
        model_info = {}  # Empty if no model
        code_info = {'stargazers_count': 50000, 'forks_count': 15000}  # GitHub data
        model_readme = """  # Empty if no model
        This is a comprehensive library for machine learning tasks.
        Installation instructions are provided below with detailed examples.
        The code is thoroughly tested using pytest and unittest frameworks.
        Continuous integration ensures testing reliability across versions.
        Complete documentation with usage examples and API reference.
        """ * 30  # Make it long for full reusability score
        code_readme = "testing pytest unittest ci continuous integration"  # Test keywords
        score, latency = metrics.code_quality.code_quality(model_info, code_info, model_readme, code_readme)
        assert score >= 0.8

    def test_code_bad(self):  # Poor code quality case
        model_info = {}
        code_info = {'stargazers_count': 5, 'forks_count': 1}
        model_readme = ""
        code_readme = "Basic repo"
        score, latency = metrics.code_quality.code_quality(model_info, code_info, model_readme, code_readme)
        assert score <= 0.3


class Test_performanceclaims:
    def test_bert(self):
        model_url = "https://huggingface.co/google-bert/bert-base-uncased"
        score, latency = performance_claims(model_url)
        # sample output : 0.92
        assert ((0.92 - .8) <= score <= 1 or score == 0.5)  # really big acceptance bc it's ai and ai sucks

    def test_audience(self):
        model_url = "https://huggingface.co/parvk11/audience_classifier_model"
        score, latency = performance_claims(model_url)
        # sample output: 0.15
        assert (0 <= score <= (.6))

    def test_whispertiny(self):
        model_url = "https://huggingface.co/openai/whisper-tiny/tree/main"
        score, latency = performance_claims(model_url)
        # sample output: 0.80
        assert ((0.80 - 0.2) <= score <= (0.80 + 0.2))


class Test_datasetandcodescore:
    def test_bert(self):
        code_url = "https://github.com/google-research/bert"
        dataset_url = "https://huggingface.co/datasets/bookcorpus/bookcorpus"
        model_readme = """
        ```python
        import transformers
        tokenizer = AutoTokenizer.from_pretrained("model")
        ```
        """
        score, latency = dataset_and_code_score(code_url, dataset_url, model_readme)
        # sample output: 1
        assert ((1 - 0.2) <= score <= 1 or score == 0.6)

    def test_no_urls(self):
        code_url = ""
        dataset_url = ""
        model_readme = """
        """
        score, latency = dataset_and_code_score(code_url, dataset_url, model_readme)
        # sample output: 0
        assert (score == 0)


class Test_inputmissingdataset:
    def test_seen(self):
        # Use bert-base-uncased from sample_input
        # Put the known dataset into seen
        seen_set = {"https://huggingface.co/datasets/bookcorpus/bookcorpus"}
        # Model readme
        model_path = "google-bert/bert-base-uncased"
        model_rm_url = f"https://huggingface.co/{model_path}/raw/main/README.md"
        model_readme = rq.get(model_rm_url, timeout=50)
        if model_readme.status_code == 200:
            model_readme = model_readme.text.lower()
        # Look for dataset in readme
        found = find_dataset(model_readme, seen_set)
        assert (found == "https://huggingface.co/datasets/bookcorpus/bookcorpus")

    def test_notseen(self):
        seen_set = {"https://huggingface.co/datasets/bookcorpus/bookcorpus"}
        readme = "This is a readme. We used dataset image-net.org"
        found = find_dataset(readme, seen_set)
        assert (found == "")


class Test_Size:
    def test_bert_base_uncased(self):
        # Expected NET score (weighted average), not just raspberry_pi score
        # raspberry_pi: 0.2 * 0.15 = 0.03
        # jetson_nano: 0.6 * 0.15 = 0.09
        # desktop_pc: 0.9 * 0.35 = 0.315
        # aws_server: 1.0 * 0.35 = 0.35
        # Total net score: 0.03 + 0.09 + 0.315 + 0.35 = 0.785
        max_deviation = 0.15
        expected_size = 0.785
        model_id = "google-bert/bert-base-uncased"
        size_scores, actual_size, actual_latency = calculate_size_score(model_id)
        assert actual_size <= (min(1, expected_size + max_deviation)) and actual_size >= (max(0, expected_size - max_deviation))

    def test_audience_classifier_model(self):
        # Expected NET score (weighted average)
        # raspberry_pi: 0.75 * 0.15 = 0.1125
        # jetson_nano: 0.875 * 0.15 = 0.13125
        # desktop_pc: 0.96875 * 0.35 = 0.3390625
        # aws_server: 1.0 * 0.35 = 0.35
        # Total net score: ~0.933
        max_deviation = 0.15
        expected_size = 0.933
        model_id = "parvk11/audience_classifier_model"
        size_scores, actual_size, actual_latency = calculate_size_score(model_id)
        assert actual_size <= (min(1, expected_size + max_deviation)) and actual_size >= (max(0, expected_size - max_deviation))

    def test_whisper_tiny(self):
        # Expected NET score (weighted average)
        # raspberry_pi: 0.9 * 0.15 = 0.135
        # jetson_nano: 0.95 * 0.15 = 0.1425
        # desktop_pc: 0.9875 * 0.35 = 0.345625
        # aws_server: 1.0 * 0.35 = 0.35
        # Total net score: ~0.97
        max_deviation = 0.15
        expected_size = 0.97
        model_id = "openai/whisper-tiny"
        size_scores, actual_size, actual_latency = calculate_size_score(model_id)
        assert actual_size <= (min(1, expected_size + max_deviation)) and actual_size >= (max(0, expected_size - max_deviation))

    def test_calculate_size_score_with_dict_input(self):
        model_input = {'model_id': 'google-bert/bert-base-uncased'}
        scores, net_score, latency = calculate_size_score(model_input)
        assert isinstance(scores, dict)
        assert 0 <= net_score <= 1
        assert latency >= 0

    def test_calculate_size_score_with_empty_dict(self):
        model_input = {}
        scores, net_score, latency = calculate_size_score(model_input)
        assert scores == {}
        assert net_score == 0.0
        assert latency == 0

    def test_calculate_size_score_with_name_dict(self):
        model_input = {'name': 'google-bert/bert-base-uncased'}
        scores, net_score, latency = calculate_size_score(model_input)
        assert isinstance(scores, dict)
        assert 0 <= net_score <= 1
        assert latency >= 0

    def test_calculate_size_score_with_url_dict(self):
        model_input = {'url': 'https://huggingface.co/google-bert/bert-base-uncased'}
        scores, net_score, latency = calculate_size_score(model_input)
        assert isinstance(scores, dict)
        assert 0 <= net_score <= 1
        assert latency >= 0

    def test_size_score_with_none_input(self):
        try:
            scores, net_score, latency = calculate_size_score(None)
            assert scores == {}
            assert net_score == 0.0
            assert latency == 0
        except TypeError:
            pass

    def test_main_function_execution(self):
        model_id = "google-bert/bert-base-uncased"
        scores1, net1, latency1 = calculate_size_score(model_id)
        result = get_detailed_size_score(model_id)
        scores2, net2, latency2 = calculate_size_score_cached(model_id)
        assert isinstance(scores1, dict)
        assert 0 <= net1 <= 1
        assert latency1 >= 0
        assert 'size_score' in result
        assert isinstance(scores2, dict)
        assert 0 <= net2 <= 1

    # ---------- Tests for get_detailed_size_score ----------
    def test_get_detailed_size_score(self):
        model_id = "google-bert/bert-base-uncased"
        result = get_detailed_size_score(model_id)
        assert 'size_score' in result
        assert 'size_score_latency' in result
        assert isinstance(result['size_score'], dict)
        assert isinstance(result['size_score_latency'], int)
        assert 'raspberry_pi' in result['size_score']
        assert 'jetson_nano' in result['size_score']
        assert 'desktop_pc' in result['size_score']
        assert 'aws_server' in result['size_score']
        assert result['size_score_latency'] >= 0

    def test_detailed_size_score_with_dict_input(self):
        model_input = {'model_id': 'google-bert/bert-base-uncased'}
        result = get_detailed_size_score(model_input)
        assert 'size_score' in result
        assert 'size_score_latency' in result
        assert isinstance(result['size_score'], dict)
        assert isinstance(result['size_score_latency'], int)

    def test_detailed_size_score_with_empty_dict(self):
        model_input = {}
        result = get_detailed_size_score(model_input)
        expected_scores = {
            'raspberry_pi': 0.0,
            'jetson_nano': 0.0,
            'desktop_pc': 0.0,
            'aws_server': 1.0
        }
        assert result['size_score'] == expected_scores
        assert result['size_score_latency'] == 0

    # ---------- Tests for calculate_size_score_cached ----------
    def test_calculate_size_score_cached(self):
        model_id = "google-bert/bert-base-uncased"
        scores1, net1, latency1 = calculate_size_score_cached(model_id)
        scores2, net2, latency2 = calculate_size_score_cached(model_id)
        assert net1 == net2
        assert scores1 == scores2

    def test_cache_clearing_and_reuse(self):
        from metrics.size import _size_cache
        _size_cache.clear()
        model_id = "google-bert/bert-base-uncased"
        assert model_id not in _size_cache
        scores1, net1, latency1 = calculate_size_score_cached(model_id)
        assert model_id in _size_cache
        scores2, net2, latency2 = calculate_size_score_cached(model_id)
        assert scores1 == scores2
        assert net1 == net2

    def test_size_cache_with_different_inputs(self):
        from metrics.size import _size_cache
        _size_cache.clear()
        model_id = "google-bert/bert-base-uncased"
        scores1, net1, latency1 = calculate_size_score_cached(model_id)
        model_dict = {'model_id': 'google-bert/bert-base-uncased'}
        scores2, net2, latency2 = calculate_size_score_cached(model_dict)
        assert net1 == net2
        assert scores1 == scores2

    # ---------- Tests for extract_model_id_from_url ----------
    def test_extract_model_id_from_url(self):
        assert extract_model_id_from_url("https://huggingface.co/google/bert") == "google/bert"
        assert extract_model_id_from_url("https://huggingface.co/google/bert/tree/main") == "google/bert"
        assert extract_model_id_from_url("google/bert") == "google/bert"
        assert extract_model_id_from_url("random text") == "random text"

    def test_extract_model_id_with_none_url(self):
        try:
            result = extract_model_id_from_url(None)
            assert result is None
        except TypeError:
            pass

    # ---------- Tests for calculate_net_size_score ----------
    def test_calculate_net_size_score(self):
        size_scores = {
            'raspberry_pi': 0.2,
            'jetson_nano': 0.6,
            'desktop_pc': 0.9,
            'aws_server': 1.0
        }
        net_score = calculate_net_size_score(size_scores)
        expected = 0.2 * 0.15 + 0.6 * 0.15 + 0.9 * 0.35 + 1.0 * 0.35
        assert abs(net_score - expected) < 0.01

    def test_net_size_score_with_empty_dict(self):
        net_score = calculate_net_size_score({})
        assert net_score == 0.0

    def test_net_size_score_with_partial_scores(self):
        size_scores = {'raspberry_pi': 0.5, 'jetson_nano': 0.7}
        net_score = calculate_net_size_score(size_scores)
        assert abs(net_score - 0.18) < 0.01

    # ---------- Tests for get_model_size_for_scoring ----------
    def test_get_model_size_for_scoring_known_models(self):
        size = get_model_size_for_scoring("google-bert/bert-base-uncased")
        assert size == 1.6
        size = get_model_size_for_scoring("parvk11/audience_classifier_model")
        assert size == 0.5
        size = get_model_size_for_scoring("openai/whisper-tiny")
        assert size == 0.2

    def test_get_model_size_for_scoring_unknown_model(self):
        size = get_model_size_for_scoring("unknown/model-123")
        assert size >= 0

    def test_get_model_size_api_error_handling(self):
        size = get_model_size_for_scoring("invalid/model/name/with/slashes")
        assert size >= 0

    # ---------- Tests for calculate_size_scores ----------
    def test_calculate_size_scores_function(self):
        model_id = "google-bert/bert-base-uncased"
        size_scores, net_score, latency = calculate_size_scores(model_id)
        assert isinstance(size_scores, dict)
        assert 'raspberry_pi' in size_scores
        assert 'jetson_nano' in size_scores
        assert 'desktop_pc' in size_scores
        assert 'aws_server' in size_scores
        assert 0 <= net_score <= 1
        assert latency >= 0
        assert 0 <= size_scores['raspberry_pi'] <= 1
        assert 0 <= size_scores['jetson_nano'] <= 1
        assert 0 <= size_scores['desktop_pc'] <= 1
        assert size_scores['aws_server'] == 1.0

    def test_size_calculation_edge_cases(self):
        size = get_model_size_for_scoring("some/unknown-model")
        assert size >= 0

    def test_size_threshold_calculations(self):
        model_id = "google-bert/bert-base-uncased"
        size_scores, net_score, latency = calculate_size_scores(model_id)
        assert abs(size_scores['raspberry_pi'] - 0.2) < 0.1
        assert abs(size_scores['jetson_nano'] - 0.6) < 0.1
        assert abs(size_scores['desktop_pc'] - 0.9) < 0.1
        assert size_scores['aws_server'] == 1.0

    def test_size_calculation_with_very_small_model(self):
        model_id = "openai/whisper-tiny"
        size_scores, net_score, latency = calculate_size_scores(model_id)
        assert size_scores['raspberry_pi'] > 0.8
        assert size_scores['jetson_nano'] > 0.9
        assert size_scores['desktop_pc'] > 0.98
        assert size_scores['aws_server'] == 1.0

    def test_calculate_size_scores_with_invalid_model(self):
        model_id = "completely/invalid-model-name-12345"
        size_scores, net_score, latency = calculate_size_scores(model_id)
        assert isinstance(size_scores, dict)
        assert 'raspberry_pi' in size_scores
        assert 'jetson_nano' in size_scores
        assert 'desktop_pc' in size_scores
        assert 'aws_server' in size_scores
        assert 0 <= net_score <= 1
        assert latency >= 0

    # ---------- Tests for SIZE_WEIGHTS ----------
    def test_size_weight_constants(self):
        expected_weights = ['raspberry_pi', 'jetson_nano', 'desktop_pc', 'aws_server']
        for weight in expected_weights:
            assert weight in SIZE_WEIGHTS
            assert 0 <= SIZE_WEIGHTS[weight] <= 1
        total_weight = sum(SIZE_WEIGHTS.values())
        assert abs(total_weight - 1.0) < 0.01


class Test_Ramp_Up_Time:
    def test_bert_base_uncased(self):
        max_deviation = 0.15
        expected_ramp_up_time = 0.9
        api_info = {'_id': '621ffdc036468d709f174338', 'id': 'google-bert/bert-base-uncased', 'private': False, 'pipeline_tag': 'fill-mask', 'library_name': 'transformers', 'tags': ['transformers', 'pytorch', 'tf', 'jax', 'rust', 'coreml', 'onnx', 'safetensors', 'bert', 'fill-mask', 'exbert', 'en', 'dataset:bookcorpus', 'dataset:wikipedia', 'arxiv:1810.04805', 'license:apache-2.0', 'autotrain_compatible', 'endpoints_compatible', 'region:us'], 'downloads': 55363806, 'likes': 2417, 'modelId': 'google-bert/bert-base-uncased', 'author': 'google-bert', 'sha': '86b5e0934494bd15c9632b12f734a8a67f723594', 'lastModified': '2024-02-19T11:06:12.000Z', 'gated': False, 'disabled': False, 'mask_token': '[MASK]', 'widgetData': [{'text': 'Paris is the [MASK] of France.'}, {'text': 'The goal of life is [MASK].'}], 'model-index': None, 'config': {'architectures': ['BertForMaskedLM'], 'model_type': 'bert', 'tokenizer_config': {}}, 'cardData': {'language': 'en', 'tags': ['exbert'], 'license': 'apache-2.0', 'datasets': ['bookcorpus', 'wikipedia']}, 'transformersInfo': {'auto_model': 'AutoModelForMaskedLM', 'pipeline_tag': 'fill-mask', 'processor': 'AutoTokenizer'}, 'siblings': [{'rfilename': '.gitattributes'}, {'rfilename': 'LICENSE'}, {'rfilename': 'README.md'}, {'rfilename': 'config.json'}, {'rfilename': 'coreml/fill-mask/float32_model.mlpackage/Data/com.apple.CoreML/model.mlmodel'}, {'rfilename': 'coreml/fill-mask/float32_model.mlpackage/Data/com.apple.CoreML/weights/weight.bin'}, {'rfilename': 'coreml/fill-mask/float32_model.mlpackage/Manifest.json'}, {'rfilename': 'flax_model.msgpack'}, {'rfilename': 'model.onnx'}, {'rfilename': 'model.safetensors'}, {'rfilename': 'pytorch_model.bin'}, {'rfilename': 'rust_model.ot'}, {'rfilename': 'tf_model.h5'}, {'rfilename': 'tokenizer.json'}, {'rfilename': 'tokenizer_config.json'}, {'rfilename': 'vocab.txt'}], 'spaces': ['mteb/leaderboard', 'microsoft/HuggingGPT', 'Vision-CAIR/minigpt4', 'lnyan/stablediffusion-infinity', 'multimodalart/latentdiffusion', 'mrfakename/MeloTTS', 'Salesforce/BLIP', 'shi-labs/Versatile-Diffusion', 'yizhangliu/Grounded-Segment-Anything', 'stepfun-ai/Step1X-Edit', 'H-Liu1997/TANGO', 'xinyu1205/recognize-anything', 'cvlab/zero123-live', 'hilamanor/audioEditing', 'alexnasa/Chain-of-Zoom', 'AIGC-Audio/AudioGPT', 'Audio-AGI/AudioSep', 'm-ric/chunk_visualizer', 'jadechoghari/OpenMusic', 'DAMO-NLP-SG/Video-LLaMA', 'gligen/demo', 'declare-lab/mustango', 'Yiwen-ntu/MeshAnything', 'exbert-project/exbert', 'shgao/EditAnything', 'LiruiZhao/Diffree', 'Vision-CAIR/MiniGPT-v2', 'multimodalart/MoDA-fast-talking-head', 'nikigoli/countgd', 'Yuliang/ECON', 'THUdyh/Oryx', 'IDEA-Research/Grounded-SAM', 'merve/Grounding_DINO_demo', 'OpenSound/CapSpeech-TTS', 'Awiny/Image2Paragraph', 'ShilongLiu/Grounding_DINO_demo', 'yangheng/Super-Resolution-Anime-Diffusion', 'liuyuan-pal/SyncDreamer', 'XiangJinYu/SPO', 'sam-hq-team/sam-hq', 'haotiz/glip-zeroshot-demo', 'Nick088/Audio-SR', 'TencentARC/BrushEdit', 'nateraw/lavila', 'abyildirim/inst-inpaint', 'Yiwen-ntu/MeshAnythingV2', 'Pinwheel/GLIP-BLIP-Object-Detection-VQA', 'Junfeng5/GLEE_demo', 'shi-labs/Matting-Anything', 'fffiloni/Video-Matting-Anything', 'burtenshaw/autotrain-mcp', 'Vision-CAIR/MiniGPT4-video', 'linfanluntan/Grounded-SAM', 'magicr/BuboGPT', 'WensongSong/Insert-Anything', 'nvidia/audio-flamingo-2', 'clip-italian/clip-italian-demo', 'OpenGVLab/InternGPT', 'mteb/leaderboard_legacy', '3DTopia/3DTopia', 'yenniejun/tokenizers-languages', 'mmlab-ntu/relate-anything-model', 'amphion/PicoAudio', 'byeongjun-park/HarmonyView', 'keras-io/bert-semantic-similarity', 'MirageML/sjc', 'fffiloni/vta-ldm', 'NAACL2022/CLIP-Caption-Reward', 'society-ethics/model-card-regulatory-check', 'fffiloni/miniGPT4-Video-Zero', 'AIGC-Audio/AudioLCM', 'Gladiator/Text-Summarizer', 'SVGRender/DiffSketcher', 'ethanchern/Anole', 'zakaria-narjis/photo-enhancer', 'LittleFrog/IntrinsicAnything', 'milyiyo/reimagine-it', 'ysharma/text-to-image-to-video', 'acmc/whatsapp-chats-finetuning-formatter', 'OpenGVLab/VideoChatGPT', 'ZebangCheng/Emotion-LLaMA', 'sonalkum/GAMA', 'topdu/OpenOCR-Demo', 'kaushalya/medclip-roco', 'AIGC-Audio/Make_An_Audio', 'avid-ml/bias-detection', 'RitaParadaRamos/SmallCapDemo', 'llizhx/TinyGPT-V', 'codelion/Grounding_DINO_demo', 'flosstradamus/FluxMusicGUI', 'kevinwang676/E2-F5-TTS', 'bartar/tokenizers', 'Tinkering/Pytorch-day-prez', 'sasha/BiasDetection', 'Pusheen/LoCo', 'Jingkang/EgoGPT-7B', 'flax-community/koclip', 'TencentARC/VLog', 'ynhe/AskAnything', 'Volkopat/SegmentAnythingxGroundingDINO'], 'createdAt': '2022-03-02T23:29:04.000Z', 'safetensors': {'parameters': {'F32': 110106428}, 'total': 110106428}, 'inference': 'warm', 'usedStorage': 13397387509}
        actual_ramp_up_time, actual_latency = ramp_up_time(api_info)
        assert actual_ramp_up_time <= (min(1, expected_ramp_up_time + max_deviation)) and actual_ramp_up_time >= (max(0, expected_ramp_up_time - max_deviation))

    def test_audience_classifier_model(self):
        max_deviation = 0.15
        expected_ramp_up_time = 0.25
        api_info = {'_id': '680b142fdcaaa11198e4b6fc', 'id': 'parvk11/audience_classifier_model', 'private': False, 'pipeline_tag': 'text-classification', 'library_name': 'transformers', 'tags': ['transformers', 'pytorch', 'distilbert', 'text-classification', 'arxiv:1910.09700', 'autotrain_compatible', 'endpoints_compatible', 'region:us'], 'downloads': 47, 'likes': 0, 'modelId': 'parvk11/audience_classifier_model', 'author': 'parvk11', 'sha': '210023808352e2c7a1ef73025ca6d96b89f20fbe', 'lastModified': '2025-04-25T04:49:24.000Z', 'gated': False, 'disabled': False, 'mask_token': '[MASK]', 'widgetData': [{'text': 'I like you. I love you'}], 'model-index': None, 'config': {'architectures': ['DistilBertForSequenceClassification'], 'model_type': 'distilbert', 'tokenizer_config': {'cls_token': '[CLS]', 'mask_token': '[MASK]', 'pad_token': '[PAD]', 'sep_token': '[SEP]', 'unk_token': '[UNK]'}, 'additional_chat_templates': {}}, 'cardData': {'library_name': 'transformers', 'tags': []}, 'transformersInfo': {'auto_model': 'AutoModelForSequenceClassification', 'pipeline_tag': 'text-classification', 'processor': 'AutoTokenizer'}, 'siblings': [{'rfilename': '.gitattributes'}, {'rfilename': 'README.md'}, {'rfilename': 'config.json'}, {'rfilename': 'pytorch_model.bin'}, {'rfilename': 'special_tokens_map.json'}, {'rfilename': 'tokenizer_config.json'}, {'rfilename': 'vocab.txt'}], 'spaces': [], 'createdAt': '2025-04-25T04:48:47.000Z', 'usedStorage': 535693286}
        actual_ramp_up_time, actual_latency = ramp_up_time(api_info)
        assert actual_ramp_up_time <= (min(1, expected_ramp_up_time + max_deviation)) and actual_ramp_up_time >= (max(0, expected_ramp_up_time - max_deviation))

    def test_whisper_tiny(self):
        max_deviation = 0.15
        expected_ramp_up_time = 0.85
        api_info = {'_id': '63314bb6acb6472115aa55a9', 'id': 'openai/whisper-tiny', 'private': False, 'pipeline_tag': 'automatic-speech-recognition', 'library_name': 'transformers', 'tags': ['transformers', 'pytorch', 'tf', 'jax', 'safetensors', 'whisper', 'automatic-speech-recognition', 'audio', 'hf-asr-leaderboard', 'en', 'zh', 'de', 'es', 'ru', 'ko', 'fr', 'ja', 'pt', 'tr', 'pl', 'ca', 'nl', 'ar', 'sv', 'it', 'id', 'hi', 'fi', 'vi', 'he', 'uk', 'el', 'ms', 'cs', 'ro', 'da', 'hu', 'ta', 'no', 'th', 'ur', 'hr', 'bg', 'lt', 'la', 'mi', 'ml', 'cy', 'sk', 'te', 'fa', 'lv', 'bn', 'sr', 'az', 'sl', 'kn', 'et', 'mk', 'br', 'eu', 'is', 'hy', 'ne', 'mn', 'bs', 'kk', 'sq', 'sw', 'gl', 'mr', 'pa', 'si', 'km', 'sn', 'yo', 'so', 'af', 'oc', 'ka', 'be', 'tg', 'sd', 'gu', 'am', 'yi', 'lo', 'uz', 'fo', 'ht', 'ps', 'tk', 'nn', 'mt', 'sa', 'lb', 'my', 'bo', 'tl', 'mg', 'as', 'tt', 'haw', 'ln', 'ha', 'ba', 'jw', 'su', 'arxiv:2212.04356', 'license:apache-2.0', 'model-index', 'endpoints_compatible', 'region:us'], 'downloads': 524202, 'likes': 367, 'modelId': 'openai/whisper-tiny', 'author': 'openai', 'sha': '169d4a4341b33bc18d8881c4b69c2e104e1cc0af', 'lastModified': '2024-02-29T10:57:33.000Z', 'gated': False, 'disabled': False, 'widgetData': [{'example_title': 'Librispeech sample 1', 'src': 'https://cdn-media.huggingface.co/speech_samples/sample1.flac'}, {'example_title': 'Librispeech sample 2', 'src': 'https://cdn-media.huggingface.co/speech_samples/sample2.flac'}], 'model-index': [{'name': 'whisper-tiny', 'results': [{'task': {'name': 'Automatic Speech Recognition', 'type': 'automatic-speech-recognition'}, 'dataset': {'name': 'LibriSpeech (clean)', 'type': 'librispeech_asr', 'config': 'clean', 'split': 'test', 'args': {'language': 'en'}}, 'metrics': [{'name': 'Test WER', 'type': 'wer', 'value': 7.54, 'verified': False}]}, {'task': {'name': 'Automatic Speech Recognition', 'type': 'automatic-speech-recognition'}, 'dataset': {'name': 'LibriSpeech (other)', 'type': 'librispeech_asr', 'config': 'other', 'split': 'test', 'args': {'language': 'en'}}, 'metrics': [{'name': 'Test WER', 'type': 'wer', 'value': 17.15, 'verified': False}]}, {'task': {'name': 'Automatic Speech Recognition', 'type': 'automatic-speech-recognition'}, 'dataset': {'name': 'Common Voice 11.0', 'type': 'mozilla-foundation/common_voice_11_0', 'config': 'hi', 'split': 'test', 'args': {'language': 'hi'}}, 'metrics': [{'name': 'Test WER', 'type': 'wer', 'value': 141, 'verified': False}]}]}], 'config': {'architectures': ['WhisperForConditionalGeneration'], 'model_type': 'whisper', 'tokenizer_config': {'bos_token': '<|endoftext|>', 'eos_token': '<|endoftext|>', 'pad_token': '<|endoftext|>', 'unk_token': '<|endoftext|>'}}, 'cardData': {'language': ['en', 'zh', 'de', 'es', 'ru', 'ko', 'fr', 'ja', 'pt', 'tr', 'pl', 'ca', 'nl', 'ar', 'sv', 'it', 'id', 'hi', 'fi', 'vi', 'he', 'uk', 'el', 'ms', 'cs', 'ro', 'da', 'hu', 'ta', 'no', 'th', 'ur', 'hr', 'bg', 'lt', 'la', 'mi', 'ml', 'cy', 'sk', 'te', 'fa', 'lv', 'bn', 'sr', 'az', 'sl', 'kn', 'et', 'mk', 'br', 'eu', 'is', 'hy', 'ne', 'mn', 'bs', 'kk', 'sq', 'sw', 'gl', 'mr', 'pa', 'si', 'km', 'sn', 'yo', 'so', 'af', 'oc', 'ka', 'be', 'tg', 'sd', 'gu', 'am', 'yi', 'lo', 'uz', 'fo', 'ht', 'ps', 'tk', 'nn', 'mt', 'sa', 'lb', 'my', 'bo', 'tl', 'mg', 'as', 'tt', 'haw', 'ln', 'ha', 'ba', 'jw', 'su'], 'tags': ['audio', 'automatic-speech-recognition', 'hf-asr-leaderboard'], 'widget': [{'example_title': 'Librispeech sample 1', 'src': 'https://cdn-media.huggingface.co/speech_samples/sample1.flac'}, {'example_title': 'Librispeech sample 2', 'src': 'https://cdn-media.huggingface.co/speech_samples/sample2.flac'}], 'model-index': [{'name': 'whisper-tiny', 'results': [{'task': {'name': 'Automatic Speech Recognition', 'type': 'automatic-speech-recognition'}, 'dataset': {'name': 'LibriSpeech (clean)', 'type': 'librispeech_asr', 'config': 'clean', 'split': 'test', 'args': {'language': 'en'}}, 'metrics': [{'name': 'Test WER', 'type': 'wer', 'value': 7.54, 'verified': False}]}, {'task': {'name': 'Automatic Speech Recognition', 'type': 'automatic-speech-recognition'}, 'dataset': {'name': 'LibriSpeech (other)', 'type': 'librispeech_asr', 'config': 'other', 'split': 'test', 'args': {'language': 'en'}}, 'metrics': [{'name': 'Test WER', 'type': 'wer', 'value': 17.15, 'verified': False}]}, {'task': {'name': 'Automatic Speech Recognition', 'type': 'automatic-speech-recognition'}, 'dataset': {'name': 'Common Voice 11.0', 'type': 'mozilla-foundation/common_voice_11_0', 'config': 'hi', 'split': 'test', 'args': {'language': 'hi'}}, 'metrics': [{'name': 'Test WER', 'type': 'wer', 'value': 141, 'verified': False}]}]}], 'pipeline_tag': 'automatic-speech-recognition', 'license': 'apache-2.0'}, 'transformersInfo': {'auto_model': 'AutoModelForSpeechSeq2Seq', 'pipeline_tag': 'automatic-speech-recognition', 'processor': 'AutoProcessor'}, 'siblings': [{'rfilename': '.gitattributes'}, {'rfilename': 'README.md'}, {'rfilename': 'added_tokens.json'}, {'rfilename': 'config.json'}, {'rfilename': 'flax_model.msgpack'}, {'rfilename': 'generation_config.json'}, {'rfilename': 'merges.txt'}, {'rfilename': 'model.safetensors'}, {'rfilename': 'normalizer.json'}, {'rfilename': 'preprocessor_config.json'}, {'rfilename': 'pytorch_model.bin'}, {'rfilename': 'special_tokens_map.json'}, {'rfilename': 'tf_model.h5'}, {'rfilename': 'tokenizer.json'}, {'rfilename': 'tokenizer_config.json'}, {'rfilename': 'vocab.json'}], 'spaces': ['Ailyth/Multi-voice-TTS-GPT-SoVITS', 'sanchit-gandhi/whisper-jax-spaces', 'Matthijs/whisper_word_timestamps', 'OpenSound/CapSpeech-TTS', 'radames/whisper-word-level-trim', 'lmz/candle-whisper', 'VIDraft/Portrait-Animation', 'gobeldan/insanely-fast-whisper-webui', 'devilent2/whisper-v3-zero', 'kadirnar/Whisper_M2M100_BioGpt', 'speechbox/whisper-speaker-diarization', 'nvidia/audio-flamingo-2', 'Splend1dchan/BreezyVoice-Playground', 'souljoy/ChatPDF', 'ardha27/Youtube-AI-Summarizer', 'mozilla-ai/transcribe', 'innev/whisper-Base', 'JacobLinCool/BreezyVoice', 'joaogante/assisted_generation_benchmarks', 'aetheris-ai/aibom-generator', 'eustlb/whisper-vs-distil-whisper-fr', 'RaviNaik/MultiModal-Phi2', 'kevinwang676/GPT-SoVITS-Trilingual', 'TaiYouWeb/whisper-multi-model', 'hchcsuim/Automatic-Speech-Recognition-Speech-to-Text', 'ghostai1/Audio-Translator', 'CeibalUY/transcribir_audio', 'devilent2/whisper-v3-zero-dev', 'ardha27/VideoAnalyzer', 'Anupam007/Automated-Meeting-Minutes', 'Johnyquest7/medical-transcription-notes', 'renatotn7/editarVideoAtravesDeTexto', 'radames/candle-whisper', 'vakodiya/streamlit-gpt2', 'sampsontan/llama3-rag', 'invincible-jha/MentalHealthVocalBiomarkers', 'lele1894/dubbing', 'Ericboi229-gmx-co-uk/insanely-fast-whisper-webui', 'ranialahassn/languagedetectorWhisper', 'Hamam12/Hoama', 'yolloo/VoiceQ', 'renatotn7/EspacoTeste', 'IstvanPeter/openai-whisper-tiny', 'joaogabriellima/openai-whisper-tiny', 'abrar-adnan/speech-analyzer', 'ahmedghani/Inference-Endpoint-Deployment', 'GiorgiSekhniashvili/geo-whisper', 'reach-vb/whisper_word_timestamps', 'jamesyoung999/whisper_word_timestamps', 'OdiaGenAI/Olive_Whisper_ASR', 'Aryan619348/google-calendar-agent', 'seiching/ainotes', 'filben/transcrever_audio_pt', 'Tonic/WhisperFusionTest', 'sdlc/Multi-Voice', 'ricardo-lsantos/openai-whisper-tiny', 'demomodels/lyrics', 'Tohidichi/Semantic-chunker-yt-vid', 'devilent2/whisper-v3-zero-canary', 'MikeTangoEcho/asrnersbx', 'GatinhoEducado/speech-to-speech-translation', 'RenanOF/AudioTexto', 'Anupam251272/Real-Time-Language-Translator-AI', 'garyd1/AI_Mock_Interview', 'Jwrockon/ArtemisAIWhisper', 'ZealAI/Zeal-AI', 'abdullahbilal-y/ML_Playground_Dashboard', 'Anupam007/RealTime-Meeting-Notes', 'chakchakAI/CrossTalk-Translation-AI', 'Mohammed-Islem/Speech-Processing-Lab-Project-App', 'anushka027/Whispr.ai', 'Draxgabe/acuspeak-demo', 'sebibibaba/Transcripteur-Vocal', 'pareek-joshtalksai/test-hindi-2', 'amurienne/sambot', 'dwitee/ai-powered-symptom-triage', 'KNipun/Whisper-AI-Psychiatric', 'notojasv/voice-assistant-demo', 'yoshcn/openai-whisper-tiny', 'natandiasm/openai-whisper-tiny', 'Bertievidgen/openai-whisper-tiny', 'masterkill888/openai-whisper-tiny', 'awacke1/ASR-openai-whisper-tiny', 'beyond/speech2text', 'KaliJerry/openai-whisper-tiny', 'youngseo/whisper', 'Stevross/openai-whisper-tiny', 'ericckfeng/whisper-Base-Clone', 'ysoheil/whisper_word_timestamps', 'Korla/hsb_stt_demo', 'mackaber/whisper-word-level-trim', 'kevinwang676/whisper_word_timestamps_1', 'mg5812/tuning-whisper', 'mg5812/whisper-tuning', 'futranbg/S2T', 'hiwei/asr-hf-api', 'pablocst/asr-hf-api', 'Auxiliarytrinket/my-speech-to-speech-translation', 'Photon08/summarzation_test', 'Indranil08/test'], 'createdAt': '2022-09-26T06:50:30.000Z', 'safetensors': {'parameters': {'F32': 37760640}, 'total': 37760640}, 'usedStorage': 1831289730}
        actual_ramp_up_time, actual_latency = ramp_up_time(api_info)
        assert actual_ramp_up_time <= (min(1, expected_ramp_up_time + max_deviation)) and actual_ramp_up_time >= (max(0, expected_ramp_up_time - max_deviation))

    def test_bert_base_uncased_testing_no_tags(self):
        max_deviation = 0.15
        expected_ramp_up_time = 0.9
        api_info = {'_id': '621ffdc036468d709f174338', 'id': 'google-bert/bert-base-uncased', 'private': False, 'pipeline_tag': 'fill-mask', 'library_name': 'transformers', 't-a-g-s': ['transformers', 'pytorch', 'tf', 'jax', 'rust', 'coreml', 'onnx', 'safetensors', 'bert', 'fill-mask', 'exbert', 'en', 'dataset:bookcorpus', 'dataset:wikipedia', 'arxiv:1810.04805', 'license:apache-2.0', 'autotrain_compatible', 'endpoints_compatible', 'region:us'], 'downloads': 55363806, 'likes': 2417, 'modelId': 'google-bert/bert-base-uncased', 'author': 'google-bert', 'sha': '86b5e0934494bd15c9632b12f734a8a67f723594', 'lastModified': '2024-02-19T11:06:12.000Z', 'gated': False, 'disabled': False, 'mask_token': '[MASK]', 'widgetData': [{'text': 'Paris is the [MASK] of France.'}, {'text': 'The goal of life is [MASK].'}], 'model-index': None, 'config': {'architectures': ['BertForMaskedLM'], 'model_type': 'bert', 'tokenizer_config': {}}, 'cardData': {'language': 'en', 'tags': ['exbert'], 'license': 'apache-2.0', 'datasets': ['bookcorpus', 'wikipedia']}, 'transformersInfo': {'auto_model': 'AutoModelForMaskedLM', 'pipeline_tag': 'fill-mask', 'processor': 'AutoTokenizer'}, 'siblings': [{'rfilename': '.gitattributes'}, {'rfilename': 'LICENSE'}, {'rfilename': 'README.md'}, {'rfilename': 'config.json'}, {'rfilename': 'coreml/fill-mask/float32_model.mlpackage/Data/com.apple.CoreML/model.mlmodel'}, {'rfilename': 'coreml/fill-mask/float32_model.mlpackage/Data/com.apple.CoreML/weights/weight.bin'}, {'rfilename': 'coreml/fill-mask/float32_model.mlpackage/Manifest.json'}, {'rfilename': 'flax_model.msgpack'}, {'rfilename': 'model.onnx'}, {'rfilename': 'model.safetensors'}, {'rfilename': 'pytorch_model.bin'}, {'rfilename': 'rust_model.ot'}, {'rfilename': 'tf_model.h5'}, {'rfilename': 'tokenizer.json'}, {'rfilename': 'tokenizer_config.json'}, {'rfilename': 'vocab.txt'}], 'spaces': ['mteb/leaderboard', 'microsoft/HuggingGPT', 'Vision-CAIR/minigpt4', 'lnyan/stablediffusion-infinity', 'multimodalart/latentdiffusion', 'mrfakename/MeloTTS', 'Salesforce/BLIP', 'shi-labs/Versatile-Diffusion', 'yizhangliu/Grounded-Segment-Anything', 'stepfun-ai/Step1X-Edit', 'H-Liu1997/TANGO', 'xinyu1205/recognize-anything', 'cvlab/zero123-live', 'hilamanor/audioEditing', 'alexnasa/Chain-of-Zoom', 'AIGC-Audio/AudioGPT', 'Audio-AGI/AudioSep', 'm-ric/chunk_visualizer', 'jadechoghari/OpenMusic', 'DAMO-NLP-SG/Video-LLaMA', 'gligen/demo', 'declare-lab/mustango', 'Yiwen-ntu/MeshAnything', 'exbert-project/exbert', 'shgao/EditAnything', 'LiruiZhao/Diffree', 'Vision-CAIR/MiniGPT-v2', 'multimodalart/MoDA-fast-talking-head', 'nikigoli/countgd', 'Yuliang/ECON', 'THUdyh/Oryx', 'IDEA-Research/Grounded-SAM', 'merve/Grounding_DINO_demo', 'OpenSound/CapSpeech-TTS', 'Awiny/Image2Paragraph', 'ShilongLiu/Grounding_DINO_demo', 'yangheng/Super-Resolution-Anime-Diffusion', 'liuyuan-pal/SyncDreamer', 'XiangJinYu/SPO', 'sam-hq-team/sam-hq', 'haotiz/glip-zeroshot-demo', 'Nick088/Audio-SR', 'TencentARC/BrushEdit', 'nateraw/lavila', 'abyildirim/inst-inpaint', 'Yiwen-ntu/MeshAnythingV2', 'Pinwheel/GLIP-BLIP-Object-Detection-VQA', 'Junfeng5/GLEE_demo', 'shi-labs/Matting-Anything', 'fffiloni/Video-Matting-Anything', 'burtenshaw/autotrain-mcp', 'Vision-CAIR/MiniGPT4-video', 'linfanluntan/Grounded-SAM', 'magicr/BuboGPT', 'WensongSong/Insert-Anything', 'nvidia/audio-flamingo-2', 'clip-italian/clip-italian-demo', 'OpenGVLab/InternGPT', 'mteb/leaderboard_legacy', '3DTopia/3DTopia', 'yenniejun/tokenizers-languages', 'mmlab-ntu/relate-anything-model', 'amphion/PicoAudio', 'byeongjun-park/HarmonyView', 'keras-io/bert-semantic-similarity', 'MirageML/sjc', 'fffiloni/vta-ldm', 'NAACL2022/CLIP-Caption-Reward', 'society-ethics/model-card-regulatory-check', 'fffiloni/miniGPT4-Video-Zero', 'AIGC-Audio/AudioLCM', 'Gladiator/Text-Summarizer', 'SVGRender/DiffSketcher', 'ethanchern/Anole', 'zakaria-narjis/photo-enhancer', 'LittleFrog/IntrinsicAnything', 'milyiyo/reimagine-it', 'ysharma/text-to-image-to-video', 'acmc/whatsapp-chats-finetuning-formatter', 'OpenGVLab/VideoChatGPT', 'ZebangCheng/Emotion-LLaMA', 'sonalkum/GAMA', 'topdu/OpenOCR-Demo', 'kaushalya/medclip-roco', 'AIGC-Audio/Make_An_Audio', 'avid-ml/bias-detection', 'RitaParadaRamos/SmallCapDemo', 'llizhx/TinyGPT-V', 'codelion/Grounding_DINO_demo', 'flosstradamus/FluxMusicGUI', 'kevinwang676/E2-F5-TTS', 'bartar/tokenizers', 'Tinkering/Pytorch-day-prez', 'sasha/BiasDetection', 'Pusheen/LoCo', 'Jingkang/EgoGPT-7B', 'flax-community/koclip', 'TencentARC/VLog', 'ynhe/AskAnything', 'Volkopat/SegmentAnythingxGroundingDINO'], 'createdAt': '2022-03-02T23:29:04.000Z', 'safetensors': {'parameters': {'F32': 110106428}, 'total': 110106428}, 'inference': 'warm', 'usedStorage': 13397387509}
        actual_ramp_up_time, actual_latency = ramp_up_time(api_info)
        assert actual_ramp_up_time <= (min(1, expected_ramp_up_time + max_deviation)) and actual_ramp_up_time >= (max(0, expected_ramp_up_time - max_deviation))


class Test_License:
    def test_bert_base_uncased(self):
        max_deviation = 0.15
        expected_license = 1.0  # Apache 2.0 license - compatible
        model_id = "google-bert/bert-base-uncased"
        actual_license, actual_latency = get_license_score(model_id)
        assert actual_license <= (min(1, expected_license + max_deviation)) and actual_license >= (max(0, expected_license - max_deviation))

    def test_audience_classifier_model(self):
        max_deviation = 0.15
        expected_license = 0.0  # No clear license found - incompatible
        model_id = "parvk11/audience_classifier_model"
        actual_license, actual_latency = get_license_score(model_id)
        assert actual_license <= (min(1, expected_license + max_deviation)) and actual_license >= (max(0, expected_license - max_deviation))

    def test_whisper_tiny(self):
        max_deviation = 0.15
        expected_license = 1.0  # Apache 2.0 license - compatible
        model_id = "openai/whisper-tiny"
        actual_license, actual_latency = get_license_score(model_id)
        assert actual_license <= (min(1, expected_license + max_deviation)) and actual_license >= (max(0, expected_license - max_deviation))

    def test_ambiguous_license_with_positive_indicators(self):
        # Test case to cover lines 101-117: ambiguous license with positive indicators
        model_id = "microsoft/DialoGPT-small"
        actual_license, actual_latency = get_license_score(model_id)
        assert actual_license >= 0.0 and actual_license <= 1.0

    def test_ambiguous_license_no_positive_indicators(self):
        # Test case for no positive indicators (line 117)
        # This is hard to test with real models, so we'll test the function directly
        from metrics.license import analyze_license_text

        # Test text with no license indicators
        license_text = "This is some random text with no license information."
        score = analyze_license_text(license_text)
        assert score == 0.0  # Should return 0.0 for no clear license

    def test_gated_license_detection(self):
        # Test gated license detection (line 75)
        from metrics.license import analyze_license_text
        license_text = "This is a gated model requiring access request."
        score = analyze_license_text(license_text)
        assert score == 0.0  # Should return 0.0 for gated licenses

    def test_empty_license_text(self):
        # Test empty license text (line 75)
        from metrics.license import analyze_license_text
        score = analyze_license_text("")
        assert score == 0.0

    def test_none_license_text(self):
        # Test None license text
        from metrics.license import analyze_license_text
        score = analyze_license_text(None)
        assert score == 0.0

    def test_extract_license_section_edge_cases(self):
        # Test edge cases for extract_license_section - FIXED
        # Empty content
        result = extract_license_section("")
        assert result == ""

        # Content without license - FIXED: The function returns context when "license" is found
        result = extract_license_section("Some random text without license")
        # Since "license" is in the text, it will return some context around it
        assert "license" in result.lower()
        assert "random text" in result.lower()

    def test_get_license_score_with_dict_input(self):
        # Test with dictionary input containing model_id
        model_input = {'model_id': 'google-bert/bert-base-uncased'}
        score, latency = get_license_score(model_input)
        assert 0 <= score <= 1
        assert latency >= 0

    def test_get_license_score_with_empty_dict(self):
        # Test with empty dictionary (should return 0.0)
        model_input = {}
        score, latency = get_license_score(model_input)
        assert score == 0.0
        assert latency >= 0

    def test_get_license_score_with_url_dict(self):
        # Test with dictionary input containing URL
        model_input = {'url': 'https://huggingface.co/google-bert/bert-base-uncased'}
        score, latency = get_license_score(model_input)
        assert 0 <= score <= 1
        assert latency >= 0

    def test_get_detailed_license_score(self):
        # Test the detailed license score function (covers lines 306-320)
        model_id = "google-bert/bert-base-uncased"
        result = get_detailed_license_score(model_id)

        # Check the structure of the returned dictionary
        assert 'license' in result
        assert 'license_latency' in result
        assert isinstance(result['license'], float)
        assert isinstance(result['license_latency'], int)
        assert 0 <= result['license'] <= 1
        assert result['license_latency'] >= 0

    def test_get_license_score_cached(self):
        # Test the cached version (covers lines 323-342)
        model_id = "google-bert/bert-base-uncased"

        # First call
        score1, latency1 = get_license_score_cached(model_id)

        # Second call (should use cache)
        score2, latency2 = get_license_score_cached(model_id)

        # Scores should be the same
        assert score1 == score2
        # Second call should be faster (or at least not slower)
        assert latency2 <= latency1 or abs(latency2 - latency1) < 100  # Allow small variance

    def test_license_with_dict_name(self):
        # Test with dictionary input containing name
        model_input = {'name': 'google-bert/bert-base-uncased'}
        score, latency = get_license_score(model_input)
        assert 0 <= score <= 1
        assert latency >= 0

    def test_main_block_coverage(self):
        # Test to cover the main block (lines 339-342)
        # We can't easily test the main block directly, but we can test the functions it calls
        model_id = "google-bert/bert-base-uncased"
        score, latency = get_license_score_cached(model_id)
        assert 0 <= score <= 1
        assert latency >= 0

    def test_compatible_license_detection(self):
        # Test various compatible licenses
        from metrics.license import analyze_license_text
        compatible_licenses = [
            "Apache 2.0 license",
            "MIT License",
            "BSD-3-Clause",
            "BSL-1.0",
            "LGPLv2.1"
        ]
        for license_text in compatible_licenses:
            score = analyze_license_text(license_text)
            assert score == 1.0, f"Failed for: {license_text}"

    def test_incompatible_license_detection(self):
        # Test various incompatible licenses
        from metrics.license import analyze_license_text
        incompatible_licenses = [
            "GPL v3 license",
            "AGPL license",
            "Non-commercial use only",
            "Proprietary license"
        ]
        for license_text in incompatible_licenses:
            score = analyze_license_text(license_text)
            assert score == 0.0, f"Failed for: {license_text}"

    # NEW TESTS TO COVER MISSING LINES
    def test_ambiguous_license_exact_coverage(self):
        # Direct test to cover lines 101-117 specifically
        from metrics.license import analyze_license_text

        # Test case that hits the "ambiguous but positive indicators" path (line 112-115)
        license_text = "This model is open source and permissive for research use."
        score = analyze_license_text(license_text)
        # This should hit line 112 (checking for positive words) and return 0.5
        assert score == 0.5

        # Test case that hits the "no clear license found" path (line 117)
        license_text = "This is some completely random text with no license mentions."
        score = analyze_license_text(license_text)
        assert score == 0.0

    def test_download_readme_edge_cases(self):
        # Test edge cases for download_readme_directly to cover lines 139-140, 159-160
        from metrics.license import download_readme_directly

        # Test with a non-existent model to cover error handling
        result = download_readme_directly("non/existent-model-12345")
        assert result == ""  # Should return empty string for non-existent models

    def test_license_pattern_matching(self):
        # Test to cover lines 215-216, 220-221 (pattern matching edge cases)
        from metrics.license import extract_license_section

        # Test with various license header formats
        test_content = """
# Some content
## License
Apache 2.0
## Other section
More content
"""
        result = extract_license_section(test_content)
        assert "Apache" in result

        # Test with license: pattern
        test_content = "license: MIT License"
        result = extract_license_section(test_content)
        assert "MIT" in result

    def test_cache_functionality(self):
        # Test to cover lines 323-342 (caching functionality)
        model_id = "google-bert/bert-base-uncased"

        # Clear cache first
        from metrics.license import _license_cache
        _license_cache.clear()

        # First call - should calculate
        score1, latency1 = get_license_score_cached(model_id)

        # Second call - should use cache
        score2, latency2 = get_license_score_cached(model_id)

        # Verify cache is being used
        assert model_id in _license_cache
        assert score1 == score2

    def test_extract_model_id_edge_cases(self):
        # Test to cover lines 263-265 (extract_model_id edge cases)
        from metrics.license import extract_model_id_from_url

        # Test various URL formats
        assert extract_model_id_from_url("https://huggingface.co/google/bert") == "google/bert"
        assert extract_model_id_from_url("google/bert") == "google/bert"
        assert extract_model_id_from_url("random text") == "random text"

    def test_analyze_license_mixed_signals(self):
        # Test to cover line 307 and other edge cases
        from metrics.license import analyze_license_text

        # Test with both compatible and incompatible licenses (should return 0.0)
        license_text = "This uses Apache 2.0 but also has GPL components"
        score = analyze_license_text(license_text)
        assert score == 0.0  # Incompatible takes precedence

    def test_direct_license_analysis_coverage(self):
        # Direct test to hit the exact missing lines in analyze_license_text
        from metrics.license import analyze_license_text

        # Test case 1: Empty text (line 75)
        assert analyze_license_text("") == 0.0

        # Test case 2: Gated license (line 75 in the conditions)
        assert analyze_license_text("gated model access request") == 0.0

        # Test case 3: Compatible license found (should return 1.0)
        assert analyze_license_text("Apache 2.0") == 1.0

        # Test case 4: Incompatible license found (should return 0.0)
        assert analyze_license_text("GPL v3") == 0.0

        # Test case 5: Ambiguous with positive indicators (lines 112-115)
        assert analyze_license_text("open source permissive") == 0.5

        # Test case 6: No clear license (line 117)
        assert analyze_license_text("random text") == 0.0


class Test_Bus_Factor:
    def test_bert_base_uncased(self):
        max_deviation = 0.15
        expected_bus_factor = 0.95
        api_info = {'_id': '621ffdc036468d709f174338', 'id': 'google-bert/bert-base-uncased', 'private': False, 'pipeline_tag': 'fill-mask', 'library_name': 'transformers', 'tags': ['transformers', 'pytorch', 'tf', 'jax', 'rust', 'coreml', 'onnx', 'safetensors', 'bert', 'fill-mask', 'exbert', 'en', 'dataset:bookcorpus', 'dataset:wikipedia', 'arxiv:1810.04805', 'license:apache-2.0', 'autotrain_compatible', 'endpoints_compatible', 'region:us'], 'downloads': 55363806, 'likes': 2417, 'modelId': 'google-bert/bert-base-uncased', 'author': 'google-bert', 'sha': '86b5e0934494bd15c9632b12f734a8a67f723594', 'lastModified': '2024-02-19T11:06:12.000Z', 'gated': False, 'disabled': False, 'mask_token': '[MASK]', 'widgetData': [{'text': 'Paris is the [MASK] of France.'}, {'text': 'The goal of life is [MASK].'}], 'model-index': None, 'config': {'architectures': ['BertForMaskedLM'], 'model_type': 'bert', 'tokenizer_config': {}}, 'cardData': {'language': 'en', 'tags': ['exbert'], 'license': 'apache-2.0', 'datasets': ['bookcorpus', 'wikipedia']}, 'transformersInfo': {'auto_model': 'AutoModelForMaskedLM', 'pipeline_tag': 'fill-mask', 'processor': 'AutoTokenizer'}, 'siblings': [{'rfilename': '.gitattributes'}, {'rfilename': 'LICENSE'}, {'rfilename': 'README.md'}, {'rfilename': 'config.json'}, {'rfilename': 'coreml/fill-mask/float32_model.mlpackage/Data/com.apple.CoreML/model.mlmodel'}, {'rfilename': 'coreml/fill-mask/float32_model.mlpackage/Data/com.apple.CoreML/weights/weight.bin'}, {'rfilename': 'coreml/fill-mask/float32_model.mlpackage/Manifest.json'}, {'rfilename': 'flax_model.msgpack'}, {'rfilename': 'model.onnx'}, {'rfilename': 'model.safetensors'}, {'rfilename': 'pytorch_model.bin'}, {'rfilename': 'rust_model.ot'}, {'rfilename': 'tf_model.h5'}, {'rfilename': 'tokenizer.json'}, {'rfilename': 'tokenizer_config.json'}, {'rfilename': 'vocab.txt'}], 'spaces': ['mteb/leaderboard', 'microsoft/HuggingGPT', 'Vision-CAIR/minigpt4', 'lnyan/stablediffusion-infinity', 'multimodalart/latentdiffusion', 'mrfakename/MeloTTS', 'Salesforce/BLIP', 'shi-labs/Versatile-Diffusion', 'yizhangliu/Grounded-Segment-Anything', 'stepfun-ai/Step1X-Edit', 'H-Liu1997/TANGO', 'xinyu1205/recognize-anything', 'cvlab/zero123-live', 'hilamanor/audioEditing', 'alexnasa/Chain-of-Zoom', 'AIGC-Audio/AudioGPT', 'Audio-AGI/AudioSep', 'm-ric/chunk_visualizer', 'jadechoghari/OpenMusic', 'DAMO-NLP-SG/Video-LLaMA', 'gligen/demo', 'declare-lab/mustango', 'Yiwen-ntu/MeshAnything', 'exbert-project/exbert', 'shgao/EditAnything', 'LiruiZhao/Diffree', 'Vision-CAIR/MiniGPT-v2', 'multimodalart/MoDA-fast-talking-head', 'nikigoli/countgd', 'Yuliang/ECON', 'THUdyh/Oryx', 'IDEA-Research/Grounded-SAM', 'merve/Grounding_DINO_demo', 'OpenSound/CapSpeech-TTS', 'Awiny/Image2Paragraph', 'ShilongLiu/Grounding_DINO_demo', 'yangheng/Super-Resolution-Anime-Diffusion', 'liuyuan-pal/SyncDreamer', 'XiangJinYu/SPO', 'sam-hq-team/sam-hq', 'haotiz/glip-zeroshot-demo', 'Nick088/Audio-SR', 'TencentARC/BrushEdit', 'nateraw/lavila', 'abyildirim/inst-inpaint', 'Yiwen-ntu/MeshAnythingV2', 'Pinwheel/GLIP-BLIP-Object-Detection-VQA', 'Junfeng5/GLEE_demo', 'shi-labs/Matting-Anything', 'fffiloni/Video-Matting-Anything', 'burtenshaw/autotrain-mcp', 'Vision-CAIR/MiniGPT4-video', 'linfanluntan/Grounded-SAM', 'magicr/BuboGPT', 'WensongSong/Insert-Anything', 'nvidia/audio-flamingo-2', 'clip-italian/clip-italian-demo', 'OpenGVLab/InternGPT', 'mteb/leaderboard_legacy', '3DTopia/3DTopia', 'yenniejun/tokenizers-languages', 'mmlab-ntu/relate-anything-model', 'amphion/PicoAudio', 'byeongjun-park/HarmonyView', 'keras-io/bert-semantic-similarity', 'MirageML/sjc', 'fffiloni/vta-ldm', 'NAACL2022/CLIP-Caption-Reward', 'society-ethics/model-card-regulatory-check', 'fffiloni/miniGPT4-Video-Zero', 'AIGC-Audio/AudioLCM', 'Gladiator/Text-Summarizer', 'SVGRender/DiffSketcher', 'ethanchern/Anole', 'zakaria-narjis/photo-enhancer', 'LittleFrog/IntrinsicAnything', 'milyiyo/reimagine-it', 'ysharma/text-to-image-to-video', 'acmc/whatsapp-chats-finetuning-formatter', 'OpenGVLab/VideoChatGPT', 'ZebangCheng/Emotion-LLaMA', 'sonalkum/GAMA', 'topdu/OpenOCR-Demo', 'kaushalya/medclip-roco', 'AIGC-Audio/Make_An_Audio', 'avid-ml/bias-detection', 'RitaParadaRamos/SmallCapDemo', 'llizhx/TinyGPT-V', 'codelion/Grounding_DINO_demo', 'flosstradamus/FluxMusicGUI', 'kevinwang676/E2-F5-TTS', 'bartar/tokenizers', 'Tinkering/Pytorch-day-prez', 'sasha/BiasDetection', 'Pusheen/LoCo', 'Jingkang/EgoGPT-7B', 'flax-community/koclip', 'TencentARC/VLog', 'ynhe/AskAnything', 'Volkopat/SegmentAnythingxGroundingDINO'], 'createdAt': '2022-03-02T23:29:04.000Z', 'safetensors': {'parameters': {'F32': 110106428}, 'total': 110106428}, 'inference': 'warm', 'usedStorage': 13397387509}
        actual_bus_factor, actual_latency = bus_factor(api_info)
        assert actual_bus_factor <= (min(1, expected_bus_factor + max_deviation)) and actual_bus_factor >= (max(0, expected_bus_factor - max_deviation))

    def test_audience_classifier_model(self):
        max_deviation = 0.15
        expected_bus_factor = 0.33
        api_info = {'_id': '680b142fdcaaa11198e4b6fc', 'id': 'parvk11/audience_classifier_model', 'private': False, 'pipeline_tag': 'text-classification', 'library_name': 'transformers', 'tags': ['transformers', 'pytorch', 'distilbert', 'text-classification', 'arxiv:1910.09700', 'autotrain_compatible', 'endpoints_compatible', 'region:us'], 'downloads': 47, 'likes': 0, 'modelId': 'parvk11/audience_classifier_model', 'author': 'parvk11', 'sha': '210023808352e2c7a1ef73025ca6d96b89f20fbe', 'lastModified': '2025-04-25T04:49:24.000Z', 'gated': False, 'disabled': False, 'mask_token': '[MASK]', 'widgetData': [{'text': 'I like you. I love you'}], 'model-index': None, 'config': {'architectures': ['DistilBertForSequenceClassification'], 'model_type': 'distilbert', 'tokenizer_config': {'cls_token': '[CLS]', 'mask_token': '[MASK]', 'pad_token': '[PAD]', 'sep_token': '[SEP]', 'unk_token': '[UNK]'}, 'additional_chat_templates': {}}, 'cardData': {'library_name': 'transformers', 'tags': []}, 'transformersInfo': {'auto_model': 'AutoModelForSequenceClassification', 'pipeline_tag': 'text-classification', 'processor': 'AutoTokenizer'}, 'siblings': [{'rfilename': '.gitattributes'}, {'rfilename': 'README.md'}, {'rfilename': 'config.json'}, {'rfilename': 'pytorch_model.bin'}, {'rfilename': 'special_tokens_map.json'}, {'rfilename': 'tokenizer_config.json'}, {'rfilename': 'vocab.txt'}], 'spaces': [], 'createdAt': '2025-04-25T04:48:47.000Z', 'usedStorage': 535693286}
        actual_bus_factor, actual_latency = bus_factor(api_info)
        assert actual_bus_factor <= (min(1, expected_bus_factor + max_deviation)) and actual_bus_factor >= (max(0, expected_bus_factor - max_deviation))

    def test_whisper_tiny(self):
        max_deviation = 0.15
        expected_bus_factor = 0.9
        api_info = {'_id': '63314bb6acb6472115aa55a9', 'id': 'openai/whisper-tiny', 'private': False, 'pipeline_tag': 'automatic-speech-recognition', 'library_name': 'transformers', 'tags': ['transformers', 'pytorch', 'tf', 'jax', 'safetensors', 'whisper', 'automatic-speech-recognition', 'audio', 'hf-asr-leaderboard', 'en', 'zh', 'de', 'es', 'ru', 'ko', 'fr', 'ja', 'pt', 'tr', 'pl', 'ca', 'nl', 'ar', 'sv', 'it', 'id', 'hi', 'fi', 'vi', 'he', 'uk', 'el', 'ms', 'cs', 'ro', 'da', 'hu', 'ta', 'no', 'th', 'ur', 'hr', 'bg', 'lt', 'la', 'mi', 'ml', 'cy', 'sk', 'te', 'fa', 'lv', 'bn', 'sr', 'az', 'sl', 'kn', 'et', 'mk', 'br', 'eu', 'is', 'hy', 'ne', 'mn', 'bs', 'kk', 'sq', 'sw', 'gl', 'mr', 'pa', 'si', 'km', 'sn', 'yo', 'so', 'af', 'oc', 'ka', 'be', 'tg', 'sd', 'gu', 'am', 'yi', 'lo', 'uz', 'fo', 'ht', 'ps', 'tk', 'nn', 'mt', 'sa', 'lb', 'my', 'bo', 'tl', 'mg', 'as', 'tt', 'haw', 'ln', 'ha', 'ba', 'jw', 'su', 'arxiv:2212.04356', 'license:apache-2.0', 'model-index', 'endpoints_compatible', 'region:us'], 'downloads': 524202, 'likes': 367, 'modelId': 'openai/whisper-tiny', 'author': 'openai', 'sha': '169d4a4341b33bc18d8881c4b69c2e104e1cc0af', 'lastModified': '2024-02-29T10:57:33.000Z', 'gated': False, 'disabled': False, 'widgetData': [{'example_title': 'Librispeech sample 1', 'src': 'https://cdn-media.huggingface.co/speech_samples/sample1.flac'}, {'example_title': 'Librispeech sample 2', 'src': 'https://cdn-media.huggingface.co/speech_samples/sample2.flac'}], 'model-index': [{'name': 'whisper-tiny', 'results': [{'task': {'name': 'Automatic Speech Recognition', 'type': 'automatic-speech-recognition'}, 'dataset': {'name': 'LibriSpeech (clean)', 'type': 'librispeech_asr', 'config': 'clean', 'split': 'test', 'args': {'language': 'en'}}, 'metrics': [{'name': 'Test WER', 'type': 'wer', 'value': 7.54, 'verified': False}]}, {'task': {'name': 'Automatic Speech Recognition', 'type': 'automatic-speech-recognition'}, 'dataset': {'name': 'LibriSpeech (other)', 'type': 'librispeech_asr', 'config': 'other', 'split': 'test', 'args': {'language': 'en'}}, 'metrics': [{'name': 'Test WER', 'type': 'wer', 'value': 17.15, 'verified': False}]}, {'task': {'name': 'Automatic Speech Recognition', 'type': 'automatic-speech-recognition'}, 'dataset': {'name': 'Common Voice 11.0', 'type': 'mozilla-foundation/common_voice_11_0', 'config': 'hi', 'split': 'test', 'args': {'language': 'hi'}}, 'metrics': [{'name': 'Test WER', 'type': 'wer', 'value': 141, 'verified': False}]}]}], 'config': {'architectures': ['WhisperForConditionalGeneration'], 'model_type': 'whisper', 'tokenizer_config': {'bos_token': '<|endoftext|>', 'eos_token': '<|endoftext|>', 'pad_token': '<|endoftext|>', 'unk_token': '<|endoftext|>'}}, 'cardData': {'language': ['en', 'zh', 'de', 'es', 'ru', 'ko', 'fr', 'ja', 'pt', 'tr', 'pl', 'ca', 'nl', 'ar', 'sv', 'it', 'id', 'hi', 'fi', 'vi', 'he', 'uk', 'el', 'ms', 'cs', 'ro', 'da', 'hu', 'ta', 'no', 'th', 'ur', 'hr', 'bg', 'lt', 'la', 'mi', 'ml', 'cy', 'sk', 'te', 'fa', 'lv', 'bn', 'sr', 'az', 'sl', 'kn', 'et', 'mk', 'br', 'eu', 'is', 'hy', 'ne', 'mn', 'bs', 'kk', 'sq', 'sw', 'gl', 'mr', 'pa', 'si', 'km', 'sn', 'yo', 'so', 'af', 'oc', 'ka', 'be', 'tg', 'sd', 'gu', 'am', 'yi', 'lo', 'uz', 'fo', 'ht', 'ps', 'tk', 'nn', 'mt', 'sa', 'lb', 'my', 'bo', 'tl', 'mg', 'as', 'tt', 'haw', 'ln', 'ha', 'ba', 'jw', 'su'], 'tags': ['audio', 'automatic-speech-recognition', 'hf-asr-leaderboard'], 'widget': [{'example_title': 'Librispeech sample 1', 'src': 'https://cdn-media.huggingface.co/speech_samples/sample1.flac'}, {'example_title': 'Librispeech sample 2', 'src': 'https://cdn-media.huggingface.co/speech_samples/sample2.flac'}], 'model-index': [{'name': 'whisper-tiny', 'results': [{'task': {'name': 'Automatic Speech Recognition', 'type': 'automatic-speech-recognition'}, 'dataset': {'name': 'LibriSpeech (clean)', 'type': 'librispeech_asr', 'config': 'clean', 'split': 'test', 'args': {'language': 'en'}}, 'metrics': [{'name': 'Test WER', 'type': 'wer', 'value': 7.54, 'verified': False}]}, {'task': {'name': 'Automatic Speech Recognition', 'type': 'automatic-speech-recognition'}, 'dataset': {'name': 'LibriSpeech (other)', 'type': 'librispeech_asr', 'config': 'other', 'split': 'test', 'args': {'language': 'en'}}, 'metrics': [{'name': 'Test WER', 'type': 'wer', 'value': 17.15, 'verified': False}]}, {'task': {'name': 'Automatic Speech Recognition', 'type': 'automatic-speech-recognition'}, 'dataset': {'name': 'Common Voice 11.0', 'type': 'mozilla-foundation/common_voice_11_0', 'config': 'hi', 'split': 'test', 'args': {'language': 'hi'}}, 'metrics': [{'name': 'Test WER', 'type': 'wer', 'value': 141, 'verified': False}]}]}], 'pipeline_tag': 'automatic-speech-recognition', 'license': 'apache-2.0'}, 'transformersInfo': {'auto_model': 'AutoModelForSpeechSeq2Seq', 'pipeline_tag': 'automatic-speech-recognition', 'processor': 'AutoProcessor'}, 'siblings': [{'rfilename': '.gitattributes'}, {'rfilename': 'README.md'}, {'rfilename': 'added_tokens.json'}, {'rfilename': 'config.json'}, {'rfilename': 'flax_model.msgpack'}, {'rfilename': 'generation_config.json'}, {'rfilename': 'merges.txt'}, {'rfilename': 'model.safetensors'}, {'rfilename': 'normalizer.json'}, {'rfilename': 'preprocessor_config.json'}, {'rfilename': 'pytorch_model.bin'}, {'rfilename': 'special_tokens_map.json'}, {'rfilename': 'tf_model.h5'}, {'rfilename': 'tokenizer.json'}, {'rfilename': 'tokenizer_config.json'}, {'rfilename': 'vocab.json'}], 'spaces': ['Ailyth/Multi-voice-TTS-GPT-SoVITS', 'sanchit-gandhi/whisper-jax-spaces', 'Matthijs/whisper_word_timestamps', 'OpenSound/CapSpeech-TTS', 'radames/whisper-word-level-trim', 'lmz/candle-whisper', 'VIDraft/Portrait-Animation', 'gobeldan/insanely-fast-whisper-webui', 'devilent2/whisper-v3-zero', 'kadirnar/Whisper_M2M100_BioGpt', 'speechbox/whisper-speaker-diarization', 'nvidia/audio-flamingo-2', 'Splend1dchan/BreezyVoice-Playground', 'souljoy/ChatPDF', 'ardha27/Youtube-AI-Summarizer', 'mozilla-ai/transcribe', 'innev/whisper-Base', 'JacobLinCool/BreezyVoice', 'joaogante/assisted_generation_benchmarks', 'aetheris-ai/aibom-generator', 'eustlb/whisper-vs-distil-whisper-fr', 'RaviNaik/MultiModal-Phi2', 'kevinwang676/GPT-SoVITS-Trilingual', 'TaiYouWeb/whisper-multi-model', 'hchcsuim/Automatic-Speech-Recognition-Speech-to-Text', 'ghostai1/Audio-Translator', 'CeibalUY/transcribir_audio', 'devilent2/whisper-v3-zero-dev', 'ardha27/VideoAnalyzer', 'Anupam007/Automated-Meeting-Minutes', 'Johnyquest7/medical-transcription-notes', 'renatotn7/editarVideoAtravesDeTexto', 'radames/candle-whisper', 'vakodiya/streamlit-gpt2', 'sampsontan/llama3-rag', 'invincible-jha/MentalHealthVocalBiomarkers', 'lele1894/dubbing', 'Ericboi229-gmx-co-uk/insanely-fast-whisper-webui', 'ranialahassn/languagedetectorWhisper', 'Hamam12/Hoama', 'yolloo/VoiceQ', 'renatotn7/EspacoTeste', 'IstvanPeter/openai-whisper-tiny', 'joaogabriellima/openai-whisper-tiny', 'abrar-adnan/speech-analyzer', 'ahmedghani/Inference-Endpoint-Deployment', 'GiorgiSekhniashvili/geo-whisper', 'reach-vb/whisper_word_timestamps', 'jamesyoung999/whisper_word_timestamps', 'OdiaGenAI/Olive_Whisper_ASR', 'Aryan619348/google-calendar-agent', 'seiching/ainotes', 'filben/transcrever_audio_pt', 'Tonic/WhisperFusionTest', 'sdlc/Multi-Voice', 'ricardo-lsantos/openai-whisper-tiny', 'demomodels/lyrics', 'Tohidichi/Semantic-chunker-yt-vid', 'devilent2/whisper-v3-zero-canary', 'MikeTangoEcho/asrnersbx', 'GatinhoEducado/speech-to-speech-translation', 'RenanOF/AudioTexto', 'Anupam251272/Real-Time-Language-Translator-AI', 'garyd1/AI_Mock_Interview', 'Jwrockon/ArtemisAIWhisper', 'ZealAI/Zeal-AI', 'abdullahbilal-y/ML_Playground_Dashboard', 'Anupam007/RealTime-Meeting-Notes', 'chakchakAI/CrossTalk-Translation-AI', 'Mohammed-Islem/Speech-Processing-Lab-Project-App', 'anushka027/Whispr.ai', 'Draxgabe/acuspeak-demo', 'sebibibaba/Transcripteur-Vocal', 'pareek-joshtalksai/test-hindi-2', 'amurienne/sambot', 'dwitee/ai-powered-symptom-triage', 'KNipun/Whisper-AI-Psychiatric', 'notojasv/voice-assistant-demo', 'yoshcn/openai-whisper-tiny', 'natandiasm/openai-whisper-tiny', 'Bertievidgen/openai-whisper-tiny', 'masterkill888/openai-whisper-tiny', 'awacke1/ASR-openai-whisper-tiny', 'beyond/speech2text', 'KaliJerry/openai-whisper-tiny', 'youngseo/whisper', 'Stevross/openai-whisper-tiny', 'ericckfeng/whisper-Base-Clone', 'ysoheil/whisper_word_timestamps', 'Korla/hsb_stt_demo', 'mackaber/whisper-word-level-trim', 'kevinwang676/whisper_word_timestamps_1', 'mg5812/tuning-whisper', 'mg5812/whisper-tuning', 'futranbg/S2T', 'hiwei/asr-hf-api', 'pablocst/asr-hf-api', 'Auxiliarytrinket/my-speech-to-speech-translation', 'Photon08/summarzation_test', 'Indranil08/test'], 'createdAt': '2022-09-26T06:50:30.000Z', 'safetensors': {'parameters': {'F32': 37760640}, 'total': 37760640}, 'usedStorage': 1831289730}
        actual_bus_factor, actual_latency = bus_factor(api_info)
        assert actual_bus_factor <= (min(1, expected_bus_factor + max_deviation)) and actual_bus_factor >= (max(0, expected_bus_factor - max_deviation))


class Test_Input:

    def test_find_dataset_found(self):
        readme = "this model was trained using dataset1 from huggingface"
        seen = {"https://huggingface.co/datasets/dataset1"}
        result = find_dataset(readme, seen)
        assert result == "https://huggingface.co/datasets/dataset1"

    def test_find_dataset_not_found(self):
        readme = "no known dataset mentioned here"
        seen = {"https://huggingface.co/datasets/dataset2"}
        result = find_dataset(readme, seen)
        assert result == ""

    @patch("builtins.open", new_callable=mock_open, read_data="https://github.com/user/repo,https://huggingface.co/datasets/dataset1,https://huggingface.co/models/model1\n")
    @patch("requests.get")
    @patch("input.metric_concurrent.main")
    def test_main_runs_successfully(self, mock_metric_main, mock_requests_get, mock_file):
        # Fake API responses
        model_api_response = MagicMock()
        model_api_response.status_code = 200
        model_api_response.json.return_value = {"mock": "model_info"}

        readme_response = MagicMock()
        readme_response.status_code = 200
        readme_response.text = "this is a readme containing dataset1"

        code_api_response = MagicMock()
        code_api_response.status_code = 200
        code_api_response.json.return_value = {"mock": "code_info"}

        # Github readme
        code_readme_response = MagicMock()
        code_readme_response.status_code = 200
        code_readme_response.text = "code readme with stuff"

        # Define the sequence of responses
        mock_requests_get.side_effect = [
            model_api_response,  # model API
            readme_response,     # model README
            model_api_response,  # dataset API
            readme_response,     # dataset README
            code_api_response,   # GitHub repo API
            code_readme_response  # GitHub README
        ]

        # Fake sys.argv
        with patch.object(input.sys, 'argv', ["input.py", "fake_input.txt"]):
            main()

        assert mock_metric_main.called
        assert mock_requests_get.call_count == 6


# ===== NEW METRIC TESTS =====

class Test_Reproducibility:
    def test_reproducibility_with_examples(self):
        """Test reproducibility finds examples"""
        model_info = {'siblings': [{'rfilename': 'example.py'}]}
        code_info = {'full_name': 'test/repo'}
        model_readme = "Basic README"

        from metrics.reproducibility import reproducibility
        score, latency = reproducibility(model_info, code_info, model_readme)

        assert score == 1.0
        assert latency >= 0

    def test_reproducibility_with_readme_code(self):
        """Test reproducibility finds code in README"""
        model_info = {'siblings': []}
        code_info = {'full_name': 'test/repo'}
        model_readme = """
        ```python
        import transformers
        tokenizer = AutoTokenizer.from_pretrained("model")
        ```
        """

        from metrics.reproducibility import reproducibility
        score, latency = reproducibility(model_info, code_info, model_readme)

        assert score == 1.0
        assert latency >= 0

    def test_reproducibility_no_examples(self):
        """Test reproducibility with no examples"""
        model_info = {'siblings': [{'rfilename': 'config.json'}]}
        code_info = {'full_name': 'test/repo'}
        model_readme = "Basic README"

        from metrics.reproducibility import reproducibility
        score, latency = reproducibility(model_info, code_info, model_readme)

        assert score == 0.0
        assert latency >= 0


class Test_Reviewedness:
    @patch('requests.get')
    def test_reviewedness_high_rate(self, mock_get):
        """Test reviewedness with high review rate"""
        prs_response = MagicMock()
        prs_response.status_code = 200
        prs_response.json.return_value = [
            {'number': 1, 'created_at': '2024-01-01T00:00:00Z', 'url': 'https://api.github.com/repos/test/repo/pulls/1'},
            {'number': 2, 'created_at': '2024-06-01T00:00:00Z', 'url': 'https://api.github.com/repos/test/repo/pulls/2'}
        ]

        reviews_response = MagicMock()
        reviews_response.status_code = 200
        reviews_response.json.return_value = [{'id': 1, 'state': 'APPROVED'}]

        # Mock should return PRs first, then reviews for each PR
        mock_get.side_effect = [prs_response, reviews_response, reviews_response]

        from metrics.reviewedness import reviewedness
        score, latency = reviewedness({'full_name': 'test/repo'})

        # With 2 PRs both having reviews, fraction = 1.0, so score should be 1.0
        assert score == 1.0
        assert latency >= 0

    def test_reviewedness_no_repo(self):
        """Test reviewedness with no GitHub repo"""
        from metrics.reviewedness import reviewedness
        score, latency = reviewedness({})

        assert score == -1.0
        assert latency >= 0


class Test_Treescore:
    @patch('metrics.treescore.model_info')
    def test_treescore_with_parents(self, mock_model_info):
        """Test treescore with parent models"""
        parent_info = MagicMock()
        parent_info.downloads = 1000000
        parent_info.likes = 500
        parent_info.siblings = [MagicMock(rfilename='README.md')]

        mock_model_info.return_value = parent_info

        model_info = {'cardData': {'base_model': 'parent-model'}}

        from metrics.treescore import treescore
        score, latency = treescore(model_info)

        assert 0.0 <= score <= 1.0
        assert latency >= 0

    def test_treescore_no_parents(self):
        """Test treescore with no parent models"""
        from metrics.treescore import treescore
        score, latency = treescore({'cardData': {}})

        assert score == 0.0
        assert latency >= 0


class Test_LoggingMiddleware(IsolatedAsyncioTestCase):
    """Tests for backend.middleware.logging.LoggingMiddleware"""

    async def test_successful_request_logging(self):
        """Test that successful requests are logged and metrics sent"""
        from fastapi import Request, Response

        import backend.middleware.logging as logging_module

        with patch('backend.middleware.logging.boto3', create=True) as mock_boto3, \
             patch('backend.middleware.logging.CLOUDWATCH_AVAILABLE', True), \
             patch('backend.middleware.logging.logger') as mock_logger, \
             patch.object(logging_module, 'LOG_LEVEL', 1):

            mock_cloudwatch = MagicMock()
            mock_boto3.client.return_value = mock_cloudwatch

            mock_request = MagicMock(spec=Request)
            mock_request.method = "GET"
            mock_request.url.path = "/api/v1/package/"
            mock_request.client.host = "127.0.0.1"

            mock_response = Response(status_code=200)

            async def mock_call_next(request):
                return mock_response

            from backend.middleware.logging import LoggingMiddleware
            middleware = LoggingMiddleware(MagicMock())
            result = await middleware.dispatch(mock_request, mock_call_next)

            assert result == mock_response
            mock_logger.info.assert_called_once()
            log_msg = mock_logger.info.call_args[0][0]
            assert "Request: GET /api/v1/package/" in log_msg
            assert "Status: 200" in log_msg

            mock_cloudwatch.put_metric_data.assert_called_once()
            assert mock_cloudwatch.put_metric_data.call_args[1]['Namespace'] == 'ECE461/API'

    async def test_error_request_logging(self):
        """Test that errors are logged and error metrics sent"""
        from fastapi import Request

        import backend.middleware.logging as logging_module

        with patch('backend.middleware.logging.boto3', create=True) as mock_boto3, \
             patch('backend.middleware.logging.CLOUDWATCH_AVAILABLE', True), \
             patch('backend.middleware.logging.logger') as mock_logger, \
             patch.object(logging_module, 'LOG_LEVEL', 1):

            mock_cloudwatch = MagicMock()
            mock_boto3.client.return_value = mock_cloudwatch

            mock_request = MagicMock(spec=Request)
            mock_request.method = "POST"
            mock_request.url.path = "/api/v1/ingest/"
            mock_request.client.host = "10.0.1.5"

            test_error = ValueError("Test error")

            async def mock_call_next(request):
                raise test_error

            from backend.middleware.logging import LoggingMiddleware
            middleware = LoggingMiddleware(MagicMock())
            try:
                await middleware.dispatch(mock_request, mock_call_next)
                self.fail("Expected ValueError to be raised")
            except ValueError:
                pass

            mock_logger.info.assert_called_once()
            log_msg = mock_logger.info.call_args[0][0]
            assert "Error: POST /api/v1/ingest/" in log_msg
            assert "Test error" in log_msg

            mock_cloudwatch.put_metric_data.assert_called_once()

    async def test_no_logging_when_log_level_0(self):
        """Test that no logs are written when LOG_LEVEL=0 (silent mode)"""
        from fastapi import Request, Response

        import backend.middleware.logging as logging_module

        with patch('backend.middleware.logging.boto3', create=True) as mock_boto3, \
             patch('backend.middleware.logging.CLOUDWATCH_AVAILABLE', True), \
             patch('backend.middleware.logging.logger') as mock_logger, \
             patch.object(logging_module, 'LOG_LEVEL', 0):

            mock_cloudwatch = MagicMock()
            mock_boto3.client.return_value = mock_cloudwatch

            mock_request = MagicMock(spec=Request)
            mock_request.method = "GET"
            mock_request.url.path = "/health"
            mock_request.client.host = "127.0.0.1"

            async def mock_call_next(request):
                return Response(status_code=200)

            from backend.middleware.logging import LoggingMiddleware
            middleware = LoggingMiddleware(MagicMock())
            result = await middleware.dispatch(mock_request, mock_call_next)

            assert result.status_code == 200
            mock_logger.info.assert_not_called()
            mock_logger.debug.assert_not_called()
            # Metrics should still be sent (not affected by LOG_LEVEL)
            mock_cloudwatch.put_metric_data.assert_called_once()

    async def test_debug_logging_when_log_level_2(self):
        """Test that debug JSON is logged when LOG_LEVEL=2"""
        from fastapi import Request, Response

        import backend.middleware.logging as logging_module

        with patch('backend.middleware.logging.boto3', create=True) as mock_boto3, \
             patch('backend.middleware.logging.CLOUDWATCH_AVAILABLE', True), \
             patch('backend.middleware.logging.logger') as mock_logger, \
             patch.object(logging_module, 'LOG_LEVEL', 2):

            mock_cloudwatch = MagicMock()
            mock_boto3.client.return_value = mock_cloudwatch

            mock_request = MagicMock(spec=Request)
            mock_request.method = "GET"
            mock_request.url.path = "/health"
            mock_request.client.host = "127.0.0.1"

            async def mock_call_next(request):
                return Response(status_code=200)

            from backend.middleware.logging import LoggingMiddleware
            middleware = LoggingMiddleware(MagicMock())
            await middleware.dispatch(mock_request, mock_call_next)

            assert mock_logger.info.called
            assert mock_logger.debug.called
            debug_data = json.loads(mock_logger.debug.call_args[0][0])
            assert debug_data['type'] == 'request'
            assert debug_data['method'] == 'GET'

    async def test_cloudwatch_unavailable_graceful_fallback(self):
        """Test graceful fallback when CloudWatch is unavailable"""
        from fastapi import Request, Response

        import backend.middleware.logging as logging_module

        with patch('backend.middleware.logging.boto3', create=True) as mock_boto3, \
             patch('backend.middleware.logging.CLOUDWATCH_AVAILABLE', True), \
             patch('backend.middleware.logging.logger') as mock_logger, \
             patch.object(logging_module, 'LOG_LEVEL', 1):

            mock_boto3.client.side_effect = Exception("CloudWatch unavailable")

            mock_request = MagicMock(spec=Request)
            mock_request.method = "GET"
            mock_request.url.path = "/health"
            mock_request.client.host = "127.0.0.1"

            async def mock_call_next(request):
                return Response(status_code=200)

            from backend.middleware.logging import LoggingMiddleware
            middleware = LoggingMiddleware(MagicMock())
            result = await middleware.dispatch(mock_request, mock_call_next)

            assert result.status_code == 200
            assert mock_logger.info.called
            assert middleware.cloudwatch is None

    async def test_cloudwatch_metrics_failure_graceful(self):
        """Test that CloudWatch failures don't break requests"""
        from fastapi import Request, Response

        import backend.middleware.logging as logging_module

        with patch('backend.middleware.logging.boto3', create=True) as mock_boto3, \
             patch('backend.middleware.logging.CLOUDWATCH_AVAILABLE', True), \
             patch('backend.middleware.logging.logger') as mock_logger, \
             patch.object(logging_module, 'LOG_LEVEL', 1):

            mock_cloudwatch = MagicMock()
            mock_cloudwatch.put_metric_data.side_effect = Exception("CloudWatch error")
            mock_boto3.client.return_value = mock_cloudwatch

            mock_request = MagicMock(spec=Request)
            mock_request.method = "GET"
            mock_request.url.path = "/health"
            mock_request.client.host = "127.0.0.1"

            async def mock_call_next(request):
                return Response(status_code=200)

            from backend.middleware.logging import LoggingMiddleware
            middleware = LoggingMiddleware(MagicMock())
            result = await middleware.dispatch(mock_request, mock_call_next)

            assert result.status_code == 200
            assert mock_logger.info.called


class Test_Async_Model_Processing:
    """Tests for async model artifact processing functionality."""

    def test_register_model_returns_202(self):
        """Test that registering a model returns 202 Accepted."""
        from unittest.mock import patch

        from fastapi.testclient import TestClient

        from backend.app import app
        from backend.storage import memory

        memory.reset()

        with patch("backend.api.routes.artifacts.compute_model_artifact"):
            client = TestClient(app)
            payload = {"name": "test-model", "url": "https://huggingface.co/test/model"}
            response = client.post("/artifact/model", json=payload)
            assert response.status_code == 202
            assert response.json()["metadata"]["type"] == "model"

    def test_register_dataset_returns_201(self):
        """Test that registering a dataset returns 201 Created (synchronous)."""
        from fastapi.testclient import TestClient

        from backend.app import app
        from backend.storage import memory

        memory.reset()

        client = TestClient(app)
        payload = {"name": "test-dataset", "url": "https://huggingface.co/datasets/test/dataset"}
        response = client.post("/artifact/dataset", json=payload)
        assert response.status_code == 201
        assert response.json()["metadata"]["type"] == "dataset"

    def test_processing_status_update(self):
        """Test that processing status can be updated."""
        from backend.models import (Artifact, ArtifactData, ArtifactMetadata,
                                    ArtifactType)
        from backend.storage import memory

        memory.reset()

        # Create an artifact record manually to test status updates
        artifact = Artifact(
            metadata=ArtifactMetadata(id="test-id", name="test-model", type=ArtifactType.MODEL),
            data=ArtifactData(url="https://huggingface.co/test/model"),
        )
        memory.save_artifact(artifact, processing_status="processing")

        assert memory.get_processing_status("test-id") == "processing"
        memory.update_processing_status("test-id", "completed")
        assert memory.get_processing_status("test-id") == "completed"


# =============================================================================
# Health Endpoint Tests
# =============================================================================

class Test_Health_Endpoints:
    """Test suite for health check endpoints using FastAPI TestClient."""

    def test_health_endpoint_returns_ok(self):
        """Test GET /health returns 200 with correct structure."""
        from fastapi.testclient import TestClient

        from backend.app import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "uptime_seconds" in data
        assert "request_summary" in data
        assert "version" in data
        assert "components" in data

    def test_health_endpoint_request_summary_structure(self):
        """Test that request_summary has the expected fields."""
        from fastapi.testclient import TestClient

        from backend.app import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        summary = data["request_summary"]

        assert "window_start" in summary
        assert "window_end" in summary
        assert "total_requests" in summary
        assert "per_route" in summary
        assert "per_artifact_type" in summary
        assert "unique_clients" in summary

    def test_health_components_endpoint(self):
        """Test GET /health/components returns component details."""
        from fastapi.testclient import TestClient

        from backend.app import app

        client = TestClient(app)
        response = client.get("/health/components")

        assert response.status_code == 200
        data = response.json()
        assert "components" in data
        assert "generated_at" in data
        assert "window_minutes" in data
        assert len(data["components"]) > 0

    def test_health_components_with_timeline(self):
        """Test GET /health/components with include_timeline=true."""
        from fastapi.testclient import TestClient

        from backend.app import app

        client = TestClient(app)
        response = client.get("/health/components?include_timeline=true")

        assert response.status_code == 200
        data = response.json()
        assert "components" in data
        # Timeline should be present (may be empty if no requests)
        assert "timeline" in data["components"][0]

    def test_health_components_custom_window(self):
        """Test GET /health/components with custom window_minutes."""
        from fastapi.testclient import TestClient

        from backend.app import app

        client = TestClient(app)
        response = client.get("/health/components?window_minutes=30")

        assert response.status_code == 200
        data = response.json()
        assert data["window_minutes"] == 30

    def test_health_component_has_metrics(self):
        """Test that health components include metrics."""
        from fastapi.testclient import TestClient

        from backend.app import app

        client = TestClient(app)
        response = client.get("/health/components")

        assert response.status_code == 200
        data = response.json()
        component = data["components"][0]

        assert "metrics" in component
        assert "requests_per_minute" in component["metrics"]
        assert "uptime_hours" in component["metrics"]


# =============================================================================
# Metrics Tracker Tests
# =============================================================================

class Test_Metrics_Tracker:
    """Test suite for the metrics tracker service."""

    def test_get_uptime_seconds(self):
        """Test that uptime returns a positive integer."""
        from backend.services.metrics_tracker import get_uptime_seconds

        uptime = get_uptime_seconds()
        assert isinstance(uptime, int)
        assert uptime >= 0

    def test_record_request(self):
        """Test recording a request."""
        from backend.services.metrics_tracker import (get_request_summary,
                                                      record_request)

        # Record a test request
        record_request("GET", "/test-endpoint", 200, "127.0.0.1", None)

        summary = get_request_summary(60)
        assert summary["total_requests"] >= 1

    def test_get_request_summary_structure(self):
        """Test that request summary has correct structure."""
        from backend.services.metrics_tracker import get_request_summary

        summary = get_request_summary(60)

        assert "window_start" in summary
        assert "window_end" in summary
        assert "total_requests" in summary
        assert "per_route" in summary
        assert "per_artifact_type" in summary
        assert "unique_clients" in summary

    def test_get_requests_per_minute(self):
        """Test requests per minute calculation."""
        from backend.services.metrics_tracker import get_requests_per_minute

        rpm = get_requests_per_minute(60)
        assert isinstance(rpm, float)
        assert rpm >= 0

    def test_get_timeline(self):
        """Test timeline generation."""
        from backend.services.metrics_tracker import get_timeline

        timeline = get_timeline(60, 10)
        assert isinstance(timeline, list)

        # If there are entries, check structure
        if timeline:
            entry = timeline[0]
            assert "bucket" in entry
            assert "value" in entry
            assert "unit" in entry

    def test_record_request_tracks_client_ip(self):
        """Test that client IPs are tracked."""
        from backend.services.metrics_tracker import (get_request_summary,
                                                      record_request)

        record_request("GET", "/test", 200, "192.168.1.100", None)

        summary = get_request_summary(60)
        assert summary["unique_clients"] >= 1

    def test_record_request_tracks_routes(self):
        """Test that routes are tracked in per_route."""
        from backend.services.metrics_tracker import (get_request_summary,
                                                      record_request)

        record_request("GET", "/unique-test-route-12345", 200, None, None)

        summary = get_request_summary(60)
        # The route should appear in per_route
        assert isinstance(summary["per_route"], dict)
