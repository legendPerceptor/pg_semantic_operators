"""Batch processing operators for pg_semantic_operators"""

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional, TypeVar, Union

from ..client import call_model
from .ai_image import ai_image_describe, ai_image_filter

# Configure logging
logger = logging.getLogger(__name__)

# Pre-compiled regex for JSON extraction
_JSON_BLOCK_RE = re.compile(r'```json\s*(.*?)\s*```', re.DOTALL)

# Batch size constants
DEFAULT_BATCH_SIZE = 10
MAX_BATCH_SIZE = 20
MAX_IMAGE_BATCH_SIZE = 10  # OpenAI limit

T = TypeVar('T')
R = TypeVar('R')


def _parse_json_input(data: Union[str, List, Dict]) -> Optional[Union[List, Dict]]:
    """Parse JSON string or return data as-is.

    Args:
        data: JSON string, list, or dict

    Returns:
        Parsed data or None if parsing fails
    """
    if data is None:
        return None
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None
    return data


def _extract_json_array(text: str) -> Optional[List[Dict]]:
    """Extract JSON array from model response.

    Tries to find ```json ... ``` blocks first, then falls back to [...] extraction.

    Args:
        text: Model response text

    Returns:
        Parsed JSON array or None if extraction fails
    """
    if not text:
        return None

    try:
        # Try to find ```json ... ``` block
        match = _JSON_BLOCK_RE.search(text)
        if match:
            return json.loads(match.group(1))

        # Try to find [...] array
        start = text.find("[")
        end = text.rfind("]") + 1
        if 0 <= start < end:
            return json.loads(text[start:end])
    except (json.JSONDecodeError, AttributeError) as e:
        logger.debug(f"JSON extraction failed: {e}")

    return None


def _batch_executor(
    items: Union[List[T], str],
    batch_processor: Callable[[List[T], int], List[R]],
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_batch_size: int = MAX_BATCH_SIZE
) -> str:
    """Generic batch executor handling parsing, chunking, and aggregation.

    Args:
        items: List of items or JSON string
        batch_processor: Function that processes a batch and returns results
        batch_size: Desired batch size
        max_batch_size: Maximum allowed batch size

    Returns:
        JSON string of aggregated results
    """
    items = _parse_json_input(items)
    if not items:
        return "[]"

    batch_size = min(batch_size, max_batch_size)
    all_results: List[R] = []

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_results = batch_processor(batch, i)
        all_results.extend(batch_results)

    return json.dumps(all_results, ensure_ascii=False)


def _remap_indices(results: List[Dict], start_index: int) -> List[Dict]:
    """Remap local indices to global indices in batch results.

    Args:
        results: List of result dicts with 'index' keys
        start_index: Global start index for this batch

    Returns:
        Results with remapped indices
    """
    for item in results:
        if "index" in item:
            item["index"] = start_index + item["index"]
    return results


def ai_filter_batch(
    model_name: str,
    condition: str,
    rows: Union[List[Dict], str],
    batch_size: int = DEFAULT_BATCH_SIZE
) -> str:
    """
    Batch semantic filtering.

    Processes multiple rows in a single API call to improve efficiency.

    Args:
        model_name: Model name (e.g., "gpt-4o")
        condition: Filter condition in natural language
        rows: List of row data or JSON string
        batch_size: Number of rows per API call (default 10, max 20)

    Returns:
        JSON string: [{"index": 0, "result": true}, {"index": 1, "result": false}, ...]
    """
    def process_batch(batch: List[Dict], start_index: int) -> List[Dict]:
        # Build batch prompt
        items = [
            f"数据{i+1}: {json.dumps(row, ensure_ascii=False)}"
            for i, row in enumerate(batch)
        ]
        data_section = "\n".join(items)

        prompt = f"""判断以下每条数据是否满足条件: {condition}

{data_section}

输出 JSON 数组格式，每条数据必须有 "result" 字段 (true/false):
[{{"index": 0, "result": true}}, {{"index": 1, "result": false}}, ...]"""

        try:
            result = call_model(model_name, prompt)
            parsed = _extract_json_array(result)
            if parsed:
                return _remap_indices(parsed, start_index)
        except Exception as e:
            logger.error(f"Batch filter error: {e}")

        # Return False for all items on failure
        return [{"index": start_index + i, "result": False} for i in range(len(batch))]

    return _batch_executor(rows, process_batch, batch_size, MAX_BATCH_SIZE)


def ai_image_filter_batch(
    model_name: str,
    image_sources: Union[List[str], str],
    description: str,
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_workers: int = 5
) -> str:
    """
    Batch image filtering.

    Processes multiple images concurrently for improved throughput.

    Args:
        model_name: Model name
        image_sources: List of image URLs/paths or JSON string
        description: Filter description
        batch_size: Batch size (default 10, max 10 for images)
        max_workers: Maximum concurrent API calls

    Returns:
        JSON string: [{"index": 0, "result": true}, ...]
    """
    def process_batch(batch: List[str], start_index: int) -> List[Dict]:
        # Process images concurrently within the batch
        batch_results: List[Dict] = [None] * len(batch)

        with ThreadPoolExecutor(max_workers=min(max_workers, len(batch))) as executor:
            future_to_index = {
                executor.submit(ai_image_filter, model_name, source, description): i
                for i, source in enumerate(batch)
            }

            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    result = future.result()
                    batch_results[idx] = {"index": start_index + idx, "result": result}
                except Exception as e:
                    logger.error(f"Image filter error for {batch[idx]}: {e}")
                    batch_results[idx] = {"index": start_index + idx, "result": False}

        return batch_results

    return _batch_executor(image_sources, process_batch, batch_size, MAX_IMAGE_BATCH_SIZE)


def ai_image_describe_batch(
    model_name: str,
    image_sources: Union[List[str], str],
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_workers: int = 5
) -> str:
    """
    Batch image description.

    Processes multiple images concurrently for improved throughput.

    Args:
        model_name: Model name
        image_sources: List of image URLs/paths or JSON string
        batch_size: Batch size (default 10, max 10)
        max_workers: Maximum concurrent API calls

    Returns:
        JSON string: [{"index": 0, "description": "..."}, ...]
    """
    def process_batch(batch: List[str], start_index: int) -> List[Dict]:
        # Process images concurrently within the batch
        batch_results: List[Dict] = [None] * len(batch)

        with ThreadPoolExecutor(max_workers=min(max_workers, len(batch))) as executor:
            future_to_index = {
                executor.submit(ai_image_describe, model_name, source): i
                for i, source in enumerate(batch)
            }

            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    desc = future.result()
                    batch_results[idx] = {"index": start_index + idx, "description": desc}
                except Exception as e:
                    logger.error(f"Image describe error for {batch[idx]}: {e}")
                    batch_results[idx] = {"index": start_index + idx, "description": ""}

        return batch_results

    return _batch_executor(image_sources, process_batch, batch_size, MAX_IMAGE_BATCH_SIZE)


def ai_query_batch(
    model_name: str,
    prompts: Union[List[str], str],
    schema_info: Optional[str] = None,
    batch_size: int = DEFAULT_BATCH_SIZE
) -> str:
    """
    Batch SQL query generation.

    Generates multiple SQL queries in a single API call.

    Args:
        model_name: Model name
        prompts: List of user prompts or JSON string
        schema_info: Optional database schema information
        batch_size: Batch size (default 10, max 20)

    Returns:
        JSON string: [{"index": 0, "sql": "..."}, ...]
    """
    def process_batch(batch: List[str], start_index: int) -> List[Dict]:
        items = [f"问题{i+1}: {prompt}" for i, prompt in enumerate(batch)]
        schema_section = f"\n表结构: {schema_info}" if schema_info else ""

        prompt = f"""生成以下 SQL 查询:{schema_section}

{chr(10).join(items)}

输出 JSON 数组格式，每条数据必须有 "sql" 字段:
[{{"index": 0, "sql": "SELECT ..."}}, {{"index": 1, "sql": "SELECT ..."}}, ...]"""

        try:
            result = call_model(model_name, prompt)
            parsed = _extract_json_array(result)
            if parsed:
                return _remap_indices(parsed, start_index)
        except Exception as e:
            logger.error(f"Batch query error: {e}")

        # Return placeholder on failure
        return [{"index": start_index + i, "sql": "-- 错误"} for i in range(len(batch))]

    return _batch_executor(prompts, process_batch, batch_size, MAX_BATCH_SIZE)
