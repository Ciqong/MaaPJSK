import json
import time
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

import numpy as np
from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction


Point = Tuple[int, int]
Box = Tuple[int, int, int, int]


_LAST_STORY_HOME_CANDIDATE_COUNT: Optional[int] = None
_LAST_STORY_HOME_CANDIDATE_ROWS: list[int] = []


DEFAULT_PARAM: Dict[str, Any] = {
    "story_row_points": [
        [907, 623],
        [907, 510],
        [907, 397],
        [907, 284],
        [907, 171],
    ],
    "skip_badge_nodes": [
        "FlagSkipBadgeRowBottom",
        "FlagSkipBadgeRowSecond",
        "FlagSkipBadgeRowThird",
        "FlagSkipBadgeRowFourth",
        "FlagSkipBadgeRowFifth",
    ],
    "unread_badge_nodes": [
        "FlagUnreadBadgeRowBottom",
        "FlagUnreadBadgeRowSecond",
        "FlagUnreadBadgeRowThird",
        "FlagUnreadBadgeRowFourth",
        "FlagUnreadBadgeRowFifth",
    ],
    "story_list_marker_nodes": [
        "FlagStoryChapterTabs",
        "FlagStoryInfoButtonAny",
        "FlagSkipBadgeAny",
        "FlagUnreadBadgeAny",
    ],
    "story_home_marker_nodes": [
        "FlagStoryHomeConfirm",
        "FlagStoryHomeFilterButton",
    ],
    "story_home_marker_min_hits": 2,
    "story_info_button_points": [
        [-182, 623],
        [-182, 510],
        [-182, 397],
        [-182, 284],
        [-182, 171],
    ],
    "story_info_button_crop_size": [70, 70],
    "story_info_button_min_hits": 2,
    "story_info_button_min_white_pixels": 700,
    "story_info_button_min_dark_pixels": 60,
    "use_unread_badge_as_readable": False,
    "use_skip_template_without_color": False,
    "start_button_node": "FlagStartButton",
    "no_voice_button_node": "FlagNoVoiceButton",
    "next_story_checkbox_node": "FlagNextStoryCheckboxUnchecked",
    "next_story_checkbox_checked_node": "FlagNextStoryCheckboxChecked",
    "network_error_node": "FlagNetworkError",
    "download_button_node": "FlagDownloadButton",
    "story_home_confirm_node": "FlagStoryHomeConfirm",
    "continuous_read_point": [494, 475],
    "no_voice_point": [633, 540],
    "reading_click_point": [185, 352],
    "network_retry_point": [762, 424],
    "download_click_point": [785, 546],
    "compare_roi": [0, 120, 1280, 560],
    "story_start_wait": 5.0,
    "row_click_wait": 0.8,
    "reading_click_interval": 0.35,
    "reading_check_interval": 2.0,
    "min_reading_seconds": 8.0,
    "max_reading_seconds": 0.0,
    "return_diff_threshold": 0.08,
    "required_stable_hits": 2,
    "story_list_scroll_roi": [760, 160, 620, 500],
    "story_list_scroll_begin": [1070, 630],
    "story_list_scroll_end": [1070, 210],
    "story_list_scroll_duration": 220,
    "story_list_scroll_delay": 0.55,
    "story_list_scroll_max": 12,
    "story_list_scroll_stable_threshold": 0.015,
    "story_list_scroll_stable_hits": 2,
    "story_home_filter_button_ratio": [0.752, 0.063],
    "story_home_filter_option_ratio": [0.521, 0.333],
    "story_home_filter_confirm_ratio": [0.594, 0.907],
    "story_home_filter_delay": 0.8,
    "story_home_after_filter_wait": 1.0,
    "story_home_confirm_retries": 2,
    "story_home_confirm_retry_delay": 0.8,
    "story_home_card_points": [[405, 360], [350, 505], [350, 620]],
    "story_home_card_crop_size": [220, 90],
    "story_home_card_min_std": 18.0,
    "story_home_card_min_mean": 18.0,
    "no_unread_stop_node": "StopNoUnreadStory",
    "story_list_search_up_begin": [1070, 210],
    "story_list_search_up_end": [1070, 630],
    "story_list_search_up_duration": 220,
    "story_list_search_up_delay": 0.55,
    "story_list_search_up_max": 12,
    "story_list_search_up_stable_threshold": 0.015,
    "story_list_search_up_stable_hits": 2,
    "story_page_back_point": [150, 42],
    "story_page_back_wait": 1.2,
    "story_detail_back_point": [150, 42],
    "story_detail_back_wait": 1.2,
    "chapter_list_back_point": [150, 42],
    "chapter_list_back_wait": 1.2,
    "android_back_key": 4,
    "next_story_checkbox_wait": 0.3,
    "next_story_auto_read_min_markers": 2,
    "skip_color_roi": [-300, -45, 110, 55],
    "skip_color_min_pixels": 800,
    "skip_text_min_pixels": 120,
    "story_list_total_scan_enabled": True,
    "story_row_fingerprint_roi": [-520, -55, 720, 100],
}


def _load_param(raw: Any) -> Dict[str, Any]:
    if not raw:
        return dict(DEFAULT_PARAM)

    if isinstance(raw, dict):
        parsed = raw
    else:
        parsed = json.loads(raw)

    merged = dict(DEFAULT_PARAM)
    merged.update(parsed)
    return merged


def _as_point(value: Sequence[int]) -> Point:
    return int(value[0]), int(value[1])


def _click(context: Context, point: Sequence[int]) -> bool:
    x, y = _as_point(point)
    return context.tasker.controller.post_click(x, y).wait().succeeded


def _click_box_center(context: Context, box: Box) -> bool:
    x, y, width, height = box
    return _click(context, (x + max(1, width) // 2, y + max(1, height) // 2))


def _ratio_point(image: np.ndarray, ratio: Sequence[float]) -> Point:
    height, width = image.shape[:2]
    return int(round(width * float(ratio[0]))), int(round(height * float(ratio[1])))


def _image_point(image: np.ndarray, value: Sequence[int]) -> Point:
    height, width = image.shape[:2]
    x, y = int(value[0]), int(value[1])
    if x < 0:
        x = width + x
    if y < 0:
        y = height + y
    return x, y


def _screencap(context: Context) -> np.ndarray:
    job = context.tasker.controller.post_screencap().wait()
    if job.succeeded:
        return job.get()
    return context.tasker.controller.cached_image


def _recognize(context: Context, node: str, image: np.ndarray):
    detail = context.run_recognition(node, image)
    if detail and detail.hit and detail.box:
        return detail
    return None


def _crop(image: np.ndarray, roi: Sequence[int]) -> np.ndarray:
    x, y, width, height = [int(v) for v in roi]
    img_h, img_w = image.shape[:2]

    if x < 0:
        x = img_w + x
    if y < 0:
        y = img_h + y
    if width <= 0:
        width = img_w - x
    if height <= 0:
        height = img_h - y

    left = max(0, min(x, img_w - 1))
    top = max(0, min(y, img_h - 1))
    right = max(left + 1, min(left + width, img_w))
    bottom = max(top + 1, min(top + height, img_h))
    return image[top:bottom, left:right]


def _center_crop(image: np.ndarray, point: Sequence[int], size: Sequence[int]) -> np.ndarray:
    x, y = _image_point(image, point)
    width, height = [max(1, int(v)) for v in size]
    return _crop(image, [x - width // 2, y - height // 2, width, height])


def _row_relative_crop(
    image: np.ndarray,
    row_point: Sequence[int],
    roi: Sequence[int],
) -> np.ndarray:
    x_offset, y_offset, width, height = [int(v) for v in roi]
    img_h, img_w = image.shape[:2]
    row_x, row_y = _as_point(row_point)

    x = img_w + x_offset if x_offset < 0 else row_x + x_offset
    y = row_y + y_offset

    left = max(0, min(x, img_w - 1))
    top = max(0, min(y, img_h - 1))
    right = max(left + 1, min(left + max(1, width), img_w))
    bottom = max(top + 1, min(top + max(1, height), img_h))
    return image[top:bottom, left:right]


def _count_skip_marker_pixels(crop: np.ndarray) -> Tuple[int, int]:
    if crop.ndim < 3 or crop.shape[2] < 3:
        return 0, 0

    pixels = crop[..., :3].astype(np.int16)

    def make_cyan_mask(red: np.ndarray, green: np.ndarray, blue: np.ndarray) -> np.ndarray:
        return (
            (red >= 70)
            & (red <= 200)
            & (green >= 155)
            & (green <= 255)
            & (blue >= 155)
            & (blue <= 255)
            & ((green - red) >= 25)
            & ((blue - red) >= 25)
            & (np.abs(green - blue) <= 80)
        )

    def make_text_mask(red: np.ndarray, green: np.ndarray, blue: np.ndarray) -> np.ndarray:
        return (
            (red >= 45)
            & (red <= 130)
            & (green >= 45)
            & (green <= 130)
            & (blue >= 75)
            & (blue <= 180)
            & ((blue - red) >= 15)
            & ((blue - green) >= 10)
        )

    first, second, third = pixels[..., 0], pixels[..., 1], pixels[..., 2]
    rgb_cyan_mask = make_cyan_mask(first, second, third)
    bgr_cyan_mask = make_cyan_mask(third, second, first)
    rgb_text_mask = make_text_mask(first, second, third)
    bgr_text_mask = make_text_mask(third, second, first)
    return (
        int(np.count_nonzero(rgb_cyan_mask | bgr_cyan_mask)),
        int(np.count_nonzero(rgb_text_mask | bgr_text_mask)),
    )


def _row_fingerprint(image: np.ndarray, param: Dict[str, Any], row_index: int) -> Tuple[int, ...]:
    row_points = param.get("story_row_points") or []
    if row_index >= len(row_points):
        return ()

    crop = _row_relative_crop(image, row_points[row_index], param["story_row_fingerprint_roi"])
    if crop.size <= 0:
        return ()

    sample = crop[:: max(1, crop.shape[0] // 8), :: max(1, crop.shape[1] // 16)]
    if sample.ndim == 3:
        sample = np.mean(sample[..., :3], axis=2)
    quantized = np.clip(sample // 16, 0, 15).astype(np.uint8)
    return tuple(int(v) for v in quantized.flatten())


def _mean_abs_diff(left: np.ndarray, right: np.ndarray) -> float:
    height = min(left.shape[0], right.shape[0])
    width = min(left.shape[1], right.shape[1])
    if height <= 0 or width <= 0:
        return 1.0

    a = left[:height, :width].astype(np.float32)
    b = right[:height, :width].astype(np.float32)
    return float(np.mean(np.abs(a - b)) / 255.0)


def _handle_interruptions(context: Context, image: np.ndarray, param: Dict[str, Any]) -> bool:
    network_node = str(param["network_error_node"])
    network_hit = _recognize(context, network_node, image)
    if network_hit:
        _click(context, param["network_retry_point"])
        time.sleep(2.0)
        return True

    download_node = str(param["download_button_node"])
    download_hit = _recognize(context, download_node, image)
    if download_hit:
        if download_hit.box:
            _click_box_center(context, download_hit.box)
        else:
            _click(context, param["download_click_point"])
        time.sleep(2.5)
        return True

    return False


def _set_next_story_auto_read(
    context: Context,
    param: Dict[str, Any],
    enabled: bool,
) -> bool:
    unchecked_node = str(param.get("next_story_checkbox_node", ""))
    checked_node = str(param.get("next_story_checkbox_checked_node", ""))
    target_node = unchecked_node if enabled else checked_node
    if not target_node:
        return False

    image = _screencap(context)
    if _handle_interruptions(context, image, param):
        return False

    checkbox_hit = _recognize(context, target_node, image)
    if not checkbox_hit or not checkbox_hit.box:
        state = "enabled" if enabled else "disabled"
        print(f"Next-story auto read is already {state} or checkbox is not visible.")
        return False

    if not _click_box_center(context, checkbox_hit.box):
        return False

    state = "Enabled" if enabled else "Disabled"
    print(f"{state} next-story auto read.")
    time.sleep(float(param["next_story_checkbox_wait"]))
    return True


def _row_has_marker_node(
    context: Context,
    image: np.ndarray,
    nodes: Sequence[str],
    row_index: int,
    label: str,
    quiet: bool = False,
) -> bool:
    if row_index >= len(nodes):
        return False

    node = str(nodes[row_index])
    if not node:
        return False

    hit = _recognize(context, node, image)
    if hit:
        if not quiet:
            print(f"{label} marker found on visible row #{row_index + 1}.")
        return True

    return False


def _row_has_skip_color_marker(
    image: np.ndarray,
    param: Dict[str, Any],
    row_index: int,
    quiet: bool = False,
) -> bool:
    row_points = param.get("story_row_points") or []
    if row_index >= len(row_points):
        return False

    crop = _row_relative_crop(image, row_points[row_index], param["skip_color_roi"])
    cyan_pixels, text_pixels = _count_skip_marker_pixels(crop)
    if cyan_pixels < int(param["skip_color_min_pixels"]) or text_pixels < int(
        param["skip_text_min_pixels"]
    ):
        return False

    if not quiet:
        print(
            "SKIP color marker found on visible row "
            f"#{row_index + 1} ({cyan_pixels} cyan, {text_pixels} text pixels)."
        )
    return True


def _row_has_readable_marker(
    context: Context,
    image: np.ndarray,
    param: Dict[str, Any],
    row_index: int,
    quiet: bool = False,
) -> bool:
    reasons = _row_readable_reasons(context, image, param, row_index)
    if reasons:
        if not quiet:
            print(
                f"Readable marker found on visible row #{row_index + 1}: "
                f"{', '.join(reasons)}."
            )
        return True

    if not quiet:
        print(f"No SKIP/unread marker found on visible row #{row_index + 1}; skipping row.")
    return False


def _row_readable_reasons(
    context: Context,
    image: np.ndarray,
    param: Dict[str, Any],
    row_index: int,
) -> list[str]:
    skip_badge_nodes = param.get("skip_badge_nodes") or []
    unread_badge_nodes = param.get("unread_badge_nodes") or []

    reasons = []
    has_skip_template = _row_has_marker_node(
        context,
        image,
        skip_badge_nodes,
        row_index,
        "SKIP",
        True,
    )
    has_skip_color = _row_has_skip_color_marker(image, param, row_index, True)

    if has_skip_template:
        reasons.append("skip_template")
    if has_skip_color:
        reasons.append("skip_color")
    if bool(param.get("use_unread_badge_as_readable")) and _row_has_marker_node(
        context, image, unread_badge_nodes, row_index, "Unread", True
    ):
        reasons.append("unread_template")

    if has_skip_template and not has_skip_color and not bool(
        param.get("use_skip_template_without_color")
    ):
        print(
            f"SKIP template ignored on visible row #{row_index + 1}; "
            "the tight color check did not match."
        )
        reasons = [reason for reason in reasons if reason != "skip_template"]

    return reasons


def _find_readable_row_indexes(
    context: Context,
    image: np.ndarray,
    param: Dict[str, Any],
) -> list[int]:
    readable_rows = []
    row_count = len(param.get("story_row_points") or [])
    for row_index in range(row_count):
        reasons = _row_readable_reasons(context, image, param, row_index)
        if reasons:
            readable_rows.append(row_index)
            print(
                f"Chapter scan row #{row_index + 1}: readable "
                f"({', '.join(reasons)})."
            )
        else:
            print(f"Chapter scan row #{row_index + 1}: no SKIP/unread marker.")

    readable_numbers = [index + 1 for index in readable_rows]
    print(
        "Chapter unread section scan: "
        f"visible_rows={row_count}, readable_rows={len(readable_rows)}, "
        f"readable_row_numbers={readable_numbers}."
    )
    return readable_rows


def _is_story_list_visible(context: Context, image: np.ndarray, param: Dict[str, Any]) -> bool:
    for raw_node in param.get("story_list_marker_nodes") or []:
        node = str(raw_node)
        if not node:
            continue
        if _recognize(context, node, image):
            print(f"Story list marker matched: {node}.")
            return True

    if _has_story_info_button_column(image, param):
        print("Story list marker matched by info-button column.")
        return True

    return False


def _is_story_home_visible(context: Context, image: np.ndarray, param: Dict[str, Any]) -> bool:
    hits = 0
    required_hits = int(param.get("story_home_marker_min_hits", 1))
    for raw_node in param.get("story_home_marker_nodes") or []:
        node = str(raw_node)
        if not node:
            continue
        if _recognize(context, node, image):
            print(f"Story home marker matched: {node}.")
            hits += 1

    print(f"Story home marker scan: hits={hits}, required={required_hits}.")
    return hits >= required_hits

def _has_story_info_button_column(image: np.ndarray, param: Dict[str, Any]) -> bool:
    hits = 0
    points = param.get("story_info_button_points") or []
    crop_size = param.get("story_info_button_crop_size") or [1, 1]
    min_white = int(param.get("story_info_button_min_white_pixels", 0))
    min_dark = int(param.get("story_info_button_min_dark_pixels", 0))
    min_hits = int(param.get("story_info_button_min_hits", 1))

    for index, point in enumerate(points):
        crop = _center_crop(image, point, crop_size)
        if crop.ndim < 3 or crop.shape[2] < 3:
            continue

        pixels = crop[..., :3].astype(np.int16)
        red, green, blue = pixels[..., 0], pixels[..., 1], pixels[..., 2]
        max_channel = np.max(pixels, axis=2)
        min_channel = np.min(pixels, axis=2)
        white_mask = (min_channel >= 215) & ((max_channel - min_channel) <= 35)
        dark_mask = (
            (max_channel <= 170)
            & (min_channel <= 120)
            & (np.abs(red - green) <= 45)
            & (blue >= red - 10)
        )
        white_pixels = int(np.count_nonzero(white_mask))
        dark_pixels = int(np.count_nonzero(dark_mask))

        if white_pixels >= min_white and dark_pixels >= min_dark:
            hits += 1
            print(
                f"Story info button scan row #{index + 1}: hit "
                f"(white={white_pixels}, dark={dark_pixels})."
            )
        else:
            print(
                f"Story info button scan row #{index + 1}: miss "
                f"(white={white_pixels}, dark={dark_pixels})."
            )

    print(f"Story info button column scan: hits={hits}, required={min_hits}.")
    return hits >= min_hits


def _is_story_detail_visible(context: Context, image: np.ndarray, param: Dict[str, Any]) -> bool:
    detail_target = _get_story_detail_target(context, image, param)
    if not detail_target:
        return False

    target_kind, _ = detail_target
    if target_kind == "no_voice":
        print("Story detail marker matched: no-voice button.")
        return True

    print("Story detail marker matched: start button.")
    return True


def _swipe(
    context: Context,
    begin: Point,
    end: Point,
    duration: int,
) -> bool:
    return (
        context.tasker.controller.post_swipe(
            begin[0],
            begin[1],
            end[0],
            end[1],
            duration,
        )
        .wait()
        .succeeded
    )


def _press_back(context: Context, param: Dict[str, Any]) -> bool:
    print("No readable story entry remains in this story; returning to the story list.")
    return _press_back_with_point(
        context,
        param,
        param["story_page_back_point"],
        float(param["story_page_back_wait"]),
    )


def _press_back_with_point(
    context: Context,
    param: Dict[str, Any],
    point: Sequence[int],
    wait_seconds: float,
) -> bool:
    if _click(context, point):
        time.sleep(wait_seconds)
        return True

    click_key = getattr(context.tasker.controller, "post_click_key", None)
    if not click_key:
        return False

    key_job = click_key(int(param["android_back_key"])).wait()
    if not key_job.succeeded:
        return False

    time.sleep(wait_seconds)
    return True


def _return_from_chapter_list_after_reading(context: Context, param: Dict[str, Any]) -> bool:
    print("Chapter list is visible after reading; returning to the story selection page.")
    return _press_back_with_point(
        context,
        param,
        param["chapter_list_back_point"],
        float(param["chapter_list_back_wait"]),
    )


def _ensure_story_list_after_reading(context: Context, param: Dict[str, Any]) -> bool:
    image = _screencap(context)
    if _handle_interruptions(context, image, param):
        image = _screencap(context)

    if _is_story_list_visible(context, image, param):
        return _return_from_chapter_list_after_reading(context, param)

    if _is_story_home_visible(context, image, param):
        print("Outer story list is visible after reading; continuing from the story home.")
        return True

    start_target = _find_story_start_after_row_click(context, param)
    if not start_target:
        print("Chapter list is not visible yet; pressing back to return to the chapter page.")
    else:
        print("Story detail page is visible after reading; pressing back to the chapter page.")

    if not _press_back_with_point(
        context,
        param,
        param["story_detail_back_point"],
        float(param["story_detail_back_wait"]),
    ):
        return False

    image = _screencap(context)
    if _handle_interruptions(context, image, param):
        image = _screencap(context)

    if _is_story_list_visible(context, image, param):
        return _return_from_chapter_list_after_reading(context, param)

    if _is_story_home_visible(context, image, param):
        print("Returned to outer story list after reading; continuing from the story home.")
        return True

    print("Could not confirm the chapter list after pressing back.")
    return True


def _scan_story_home_candidates(image: np.ndarray, param: Dict[str, Any]) -> list[int]:
    global _LAST_STORY_HOME_CANDIDATE_COUNT, _LAST_STORY_HOME_CANDIDATE_ROWS

    candidates = []
    points = param.get("story_home_card_points") or []
    crop_size = param.get("story_home_card_crop_size") or [1, 1]
    min_std = float(param.get("story_home_card_min_std", 0.0))
    min_mean = float(param.get("story_home_card_min_mean", 0.0))

    for index, point in enumerate(points):
        crop = _center_crop(image, point, crop_size)
        mean = float(np.mean(crop)) if crop.size else 0.0
        std = float(np.std(crop)) if crop.size else 0.0
        if mean >= min_mean and std >= min_std:
            candidates.append(index)
            print(
                f"Story home scan row #{index + 1}: candidate "
                f"(mean={mean:.1f}, std={std:.1f})."
            )
        else:
            print(
                f"Story home scan row #{index + 1}: empty/disabled "
                f"(mean={mean:.1f}, std={std:.1f})."
            )

    candidate_numbers = [index + 1 for index in candidates]
    _LAST_STORY_HOME_CANDIDATE_COUNT = len(candidates)
    _LAST_STORY_HOME_CANDIDATE_ROWS = candidate_numbers
    print(
        "Story home candidate scan: "
        f"visible_slots={len(points)}, candidates={len(candidates)}, "
        f"candidate_rows={candidate_numbers}. "
        "These are only outer candidates; unread truth is checked inside the story."
    )
    return candidates


def _scroll_story_list_to_bottom(context: Context, param: Dict[str, Any]) -> np.ndarray:
    image = _screencap(context)
    previous = _crop(image, param["story_list_scroll_roi"])
    stable_hits = 0

    for index in range(int(param["story_list_scroll_max"])):
        begin = _image_point(image, param["story_list_scroll_begin"])
        end = _image_point(image, param["story_list_scroll_end"])
        if not _swipe(context, begin, end, int(param["story_list_scroll_duration"])):
            print("Story list swipe failed.")
            return image

        time.sleep(float(param["story_list_scroll_delay"]))
        image = _screencap(context)
        if _handle_interruptions(context, image, param):
            previous = _crop(image, param["story_list_scroll_roi"])
            stable_hits = 0
            continue

        current = _crop(image, param["story_list_scroll_roi"])
        diff = _mean_abs_diff(previous, current)
        print(f"Story list scroll diff #{index + 1}: {diff:.4f}")

        if diff <= float(param["story_list_scroll_stable_threshold"]):
            stable_hits += 1
            if stable_hits >= int(param["story_list_scroll_stable_hits"]):
                print("Story list reached bottom.")
                return image
        else:
            stable_hits = 0

        previous = current

    print("Story list scroll reached max attempts; using current position.")
    return image


def _search_story_list_upward_for_readable_rows(
    context: Context,
    param: Dict[str, Any],
    image: np.ndarray,
) -> Tuple[np.ndarray, list[int]]:
    previous = _crop(image, param["story_list_scroll_roi"])
    stable_hits = 0

    for index in range(int(param["story_list_search_up_max"])):
        begin = _image_point(image, param["story_list_search_up_begin"])
        end = _image_point(image, param["story_list_search_up_end"])
        if not _swipe(context, begin, end, int(param["story_list_search_up_duration"])):
            print("Story page upward search swipe failed.")
            return image, []

        time.sleep(float(param["story_list_search_up_delay"]))
        image = _screencap(context)
        if _handle_interruptions(context, image, param):
            previous = _crop(image, param["story_list_scroll_roi"])
            stable_hits = 0
            continue

        current = _crop(image, param["story_list_scroll_roi"])
        diff = _mean_abs_diff(previous, current)
        print(f"Story page upward search diff #{index + 1}: {diff:.4f}")

        readable_row_indexes = _find_readable_row_indexes(context, image, param)
        if readable_row_indexes:
            print("Readable story marker found while searching upward.")
            return image, readable_row_indexes

        if diff <= float(param["story_list_search_up_stable_threshold"]):
            stable_hits += 1
            if stable_hits >= int(param["story_list_search_up_stable_hits"]):
                print("Story page reached top during upward search.")
                return image, []
        else:
            stable_hits = 0

        previous = current

    print("Story page upward search reached max attempts; no readable entries found.")
    return image, []


def _scan_story_list_total_unread_sections(
    context: Context,
    param: Dict[str, Any],
    image: np.ndarray,
    bottom_readable_row_indexes: list[int],
) -> int:
    total = 0
    seen_fingerprints = set()

    def count_current_page(page_image: np.ndarray, readable_rows: list[int], label: str) -> int:
        subtotal = 0
        for row_index in readable_rows:
            fingerprint = _row_fingerprint(page_image, param, row_index)
            if fingerprint and fingerprint in seen_fingerprints:
                print(f"Chapter total scan {label} row #{row_index + 1}: duplicate, ignored.")
                continue
            if fingerprint:
                seen_fingerprints.add(fingerprint)
            subtotal += 1
        print(f"Chapter total scan {label}: readable_rows={len(readable_rows)}, new={subtotal}.")
        return subtotal

    total += count_current_page(image, bottom_readable_row_indexes, "bottom")
    previous = _crop(image, param["story_list_scroll_roi"])
    stable_hits = 0

    for index in range(int(param["story_list_search_up_max"])):
        begin = _image_point(image, param["story_list_search_up_begin"])
        end = _image_point(image, param["story_list_search_up_end"])
        if not _swipe(context, begin, end, int(param["story_list_search_up_duration"])):
            print("Chapter total scan swipe failed.")
            break

        time.sleep(float(param["story_list_search_up_delay"]))
        image = _screencap(context)
        if _handle_interruptions(context, image, param):
            previous = _crop(image, param["story_list_scroll_roi"])
            stable_hits = 0
            continue

        current = _crop(image, param["story_list_scroll_roi"])
        diff = _mean_abs_diff(previous, current)
        print(f"Chapter total scan upward diff #{index + 1}: {diff:.4f}")

        readable_row_indexes = _find_readable_row_indexes(context, image, param)
        total += count_current_page(image, readable_row_indexes, f"page #{index + 1}")

        if diff <= float(param["story_list_search_up_stable_threshold"]):
            stable_hits += 1
            if stable_hits >= int(param["story_list_search_up_stable_hits"]):
                print("Chapter total scan reached top.")
                break
        else:
            stable_hits = 0

        previous = current

    print(f"Chapter unread section total scan: total_readable_sections={total}.")
    return total


def _find_readable_story_page(
    context: Context,
    param: Dict[str, Any],
) -> Tuple[np.ndarray, list[int]]:
    image = _scroll_story_list_to_bottom(context, param)
    readable_row_indexes = _find_readable_row_indexes(context, image, param)
    if bool(param.get("story_list_total_scan_enabled")):
        total_readable_sections = _scan_story_list_total_unread_sections(
            context,
            param,
            image,
            readable_row_indexes,
        )
        home_count = _LAST_STORY_HOME_CANDIDATE_COUNT
        home_rows = _LAST_STORY_HOME_CANDIDATE_ROWS
        print(
            "Combined unread decision snapshot: "
            f"outer_story_candidates={home_count}, outer_candidate_rows={home_rows}, "
            f"inner_readable_sections={total_readable_sections}."
        )
        image = _scroll_story_list_to_bottom(context, param)
        readable_row_indexes = _find_readable_row_indexes(context, image, param)

    if readable_row_indexes:
        return image, readable_row_indexes

    print("No readable marker found at the bottom; searching upward in this story.")
    return _search_story_list_upward_for_readable_rows(context, param, image)


def _find_story_start_after_row_click(
    context: Context,
    param: Dict[str, Any],
) -> Optional[Tuple[str, Box]]:
    deadline = time.monotonic() + 2.5
    while time.monotonic() < deadline:
        image = _screencap(context)
        if _handle_interruptions(context, image, param):
            continue

        no_voice_node = str(param.get("no_voice_button_node", ""))
        if no_voice_node:
            no_voice_hit = _recognize(context, no_voice_node, image)
            if no_voice_hit and no_voice_hit.box:
                return "no_voice", no_voice_hit.box

        start_hit = _recognize(context, str(param["start_button_node"]), image)
        if start_hit and start_hit.box:
            return "start", start_hit.box
        time.sleep(0.25)

    return None


def _get_story_detail_target(
    context: Context,
    image: np.ndarray,
    param: Dict[str, Any],
) -> Optional[Tuple[str, Box]]:
    no_voice_node = str(param.get("no_voice_button_node", ""))
    if no_voice_node:
        no_voice_hit = _recognize(context, no_voice_node, image)
        if no_voice_hit and no_voice_hit.box:
            return "no_voice", no_voice_hit.box

    start_node = str(param.get("start_button_node", ""))
    if start_node:
        start_hit = _recognize(context, start_node, image)
        if start_hit and start_hit.box:
            return "start", start_hit.box

    return None


def _start_reading(
    context: Context,
    start_box: Box,
    param: Dict[str, Any],
    enable_next_story_auto_read: bool,
) -> bool:
    if not _click_box_center(context, start_box):
        return False

    time.sleep(0.8)
    image = _screencap(context)
    _handle_interruptions(context, image, param)

    _click(context, param["continuous_read_point"])
    time.sleep(0.8)

    image = _screencap(context)
    _handle_interruptions(context, image, param)

    _set_next_story_auto_read(context, param, enable_next_story_auto_read)

    _click(context, param["no_voice_point"])
    time.sleep(float(param["story_start_wait"]))
    return True


def _start_reading_from_row(
    context: Context,
    start_kind: str,
    start_box: Box,
    param: Dict[str, Any],
    enable_next_story_auto_read: bool,
) -> bool:
    if start_kind == "no_voice":
        _set_next_story_auto_read(context, param, enable_next_story_auto_read)
        if not _click_box_center(context, start_box):
            return False
        time.sleep(float(param["story_start_wait"]))
        return True

    return _start_reading(context, start_box, param, enable_next_story_auto_read)


def _read_until_story_list_returns(
    context: Context,
    story_list_baseline: np.ndarray,
    param: Dict[str, Any],
) -> bool:
    compare_roi = param["compare_roi"]
    baseline = _crop(story_list_baseline, compare_roi)

    started_at = time.monotonic()
    next_click_at = 0.0
    next_check_at = 0.0
    stable_hits = 0
    timeout_reported = False

    while True:
        now = time.monotonic()
        elapsed = now - started_at
        max_reading_seconds = float(param["max_reading_seconds"])
        if max_reading_seconds > 0 and elapsed > max_reading_seconds and not timeout_reported:
            print(
                "Reading loop exceeded max_reading_seconds; "
                "continuing instead of marking the task complete."
            )
            timeout_reported = True

        if now >= next_click_at:
            _click(context, param["reading_click_point"])
            next_click_at = now + float(param["reading_click_interval"])

        if now >= next_check_at:
            image = _screencap(context)
            if _handle_interruptions(context, image, param):
                stable_hits = 0
                next_check_at = time.monotonic() + float(param["reading_check_interval"])
                continue

            current = _crop(image, compare_roi)
            diff = _mean_abs_diff(baseline, current)
            print(f"Story list return diff: {diff:.4f}")

            list_visible = elapsed >= float(
                param["min_reading_seconds"]
            ) and _is_story_list_visible(context, image, param)
            detail_visible = elapsed >= float(
                param["min_reading_seconds"]
            ) and _is_story_detail_visible(context, image, param)

            if detail_visible:
                print("Story detail page returned after reading; chapter is finished.")
                return True

            home_visible = elapsed >= float(
                param["min_reading_seconds"]
            ) and _is_story_home_visible(context, image, param)

            if home_visible:
                print("Outer story list returned after reading; continuing with story selection.")
                return True

            if elapsed >= float(param["min_reading_seconds"]) and list_visible:
                stable_hits += 1
                if stable_hits >= int(param["required_stable_hits"]):
                    print("Story list returned; continuing with the next readable row.")
                    return True
            else:
                stable_hits = 0

            next_check_at = now + float(param["reading_check_interval"])

        time.sleep(0.05)


@AgentServer.custom_action("find_and_read_next_unread_story")
class FindAndReadNextUnreadStory(CustomAction):
    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        param = _load_param(argv.custom_action_param)
        story_list_baseline, readable_row_indexes = _find_readable_story_page(context, param)
        readable_row_set = set(readable_row_indexes)
        enable_next_story_auto_read = len(readable_row_indexes) >= int(
            param["next_story_auto_read_min_markers"]
        )

        if not readable_row_indexes:
            return _press_back(context, param)

        if enable_next_story_auto_read:
            print("Next-story auto read will be enabled; multiple readable stories remain.")
        else:
            print("Next-story auto read will stay disabled; only one readable story remains.")

        for row_index, row_point in enumerate(param["story_row_points"]):
            if row_index not in readable_row_set:
                print(f"No SKIP/unread marker found on visible row #{row_index + 1}; skipping row.")
                continue

            _click(context, row_point)
            time.sleep(float(param["row_click_wait"]))

            start_target = _find_story_start_after_row_click(context, param)
            if not start_target:
                continue

            start_kind, start_box = start_target
            if not _start_reading_from_row(
                context,
                start_kind,
                start_box,
                param,
                enable_next_story_auto_read,
            ):
                return False

            if not _read_until_story_list_returns(context, story_list_baseline, param):
                return False

            print("Finished a chapter; confirming the current page before rescanning.")
            return _ensure_story_list_after_reading(context, param)

        print("Readable markers were detected, but no readable row could be opened.")
        return _press_back(context, param)


@AgentServer.custom_action("set_unread_story_filter")
class SetUnreadStoryFilter(CustomAction):
    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        param = _load_param(argv.custom_action_param)
        click_delay = float(param.get("click_delay", 0.8))

        if not _click_box_center(context, argv.box):
            return False

        time.sleep(click_delay)
        image = _screencap(context)
        if not _click(context, _ratio_point(image, param["filter_option_ratio"])):
            return False

        time.sleep(click_delay)
        image = _screencap(context)
        if not _click(context, _ratio_point(image, param["filter_confirm_ratio"])):
            return False

        time.sleep(click_delay)
        return True


@AgentServer.custom_action("filter_unread_and_open_story")
class FilterUnreadAndOpenStory(CustomAction):
    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        param = _load_param(argv.custom_action_param)
        click_delay = float(param["story_home_filter_delay"])

        image = _screencap(context)
        if _handle_interruptions(context, image, param):
            image = _screencap(context)

        if not _click(context, _ratio_point(image, param["story_home_filter_button_ratio"])):
            return False

        time.sleep(click_delay)
        image = _screencap(context)
        if _handle_interruptions(context, image, param):
            return False

        if not _click(context, _ratio_point(image, param["story_home_filter_option_ratio"])):
            return False

        time.sleep(click_delay)
        image = _screencap(context)
        if _handle_interruptions(context, image, param):
            return False

        if not _click(context, _ratio_point(image, param["story_home_filter_confirm_ratio"])):
            return False

        time.sleep(float(param["story_home_after_filter_wait"]))
        story_hit = None
        for attempt in range(int(param["story_home_confirm_retries"]) + 1):
            image = _screencap(context)
            if _handle_interruptions(context, image, param):
                return False

            story_hit = _recognize(context, str(param["story_home_confirm_node"]), image)
            if story_hit and story_hit.box:
                break

            if attempt < int(param["story_home_confirm_retries"]):
                time.sleep(float(param["story_home_confirm_retry_delay"]))

        _scan_story_home_candidates(image, param)

        if not story_hit or not story_hit.box:
            print("No unread story remains after applying the unread filter.")
            stop_node = str(param["no_unread_stop_node"])
            if not context.override_next(argv.node_name, [stop_node]):
                print("Failed to override next to the no-unread stop node.")
                return False
            return True

        print("Unread filter applied; opening the selected unread story.")
        return _click_box_center(context, story_hit.box)
