import json
import time
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

import numpy as np
from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction


Point = Tuple[int, int]
Box = Tuple[int, int, int, int]


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
        "FlagStoryInfoButtonAny",
        "FlagSkipBadgeAny",
        "FlagUnreadBadgeAny",
    ],
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
    "max_reading_seconds": 900.0,
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
    "story_list_search_up_begin": [1070, 210],
    "story_list_search_up_end": [1070, 630],
    "story_list_search_up_duration": 220,
    "story_list_search_up_delay": 0.55,
    "story_list_search_up_max": 12,
    "story_list_search_up_stable_threshold": 0.015,
    "story_list_search_up_stable_hits": 2,
    "story_page_back_point": [150, 42],
    "story_page_back_wait": 1.2,
    "android_back_key": 4,
    "next_story_checkbox_wait": 0.3,
    "next_story_auto_read_min_markers": 2,
    "skip_color_roi": [-285, -48, 100, 38],
    "skip_color_min_pixels": 1200,
    "skip_text_min_pixels": 250,
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
    skip_badge_nodes = param.get("skip_badge_nodes") or []
    unread_badge_nodes = param.get("unread_badge_nodes") or []

    if _row_has_marker_node(context, image, skip_badge_nodes, row_index, "SKIP", quiet):
        return True
    if _row_has_skip_color_marker(image, param, row_index, quiet):
        return True
    if _row_has_marker_node(context, image, unread_badge_nodes, row_index, "Unread", quiet):
        return True

    if not quiet:
        print(f"No SKIP/unread marker found on visible row #{row_index + 1}; skipping row.")
    return False


def _find_readable_row_indexes(
    context: Context,
    image: np.ndarray,
    param: Dict[str, Any],
) -> list[int]:
    readable_rows = []
    row_count = len(param.get("story_row_points") or [])
    for row_index in range(row_count):
        if _row_has_readable_marker(context, image, param, row_index, quiet=True):
            readable_rows.append(row_index)

    print(f"Readable story markers on current page: {len(readable_rows)}.")
    return readable_rows


def _is_story_list_visible(context: Context, image: np.ndarray, param: Dict[str, Any]) -> bool:
    for raw_node in param.get("story_list_marker_nodes") or []:
        node = str(raw_node)
        if not node:
            continue
        if _recognize(context, node, image):
            print(f"Story list marker matched: {node}.")
            return True

    return False


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

    if _click(context, param["story_page_back_point"]):
        time.sleep(float(param["story_page_back_wait"]))
        return True

    click_key = getattr(context.tasker.controller, "post_click_key", None)
    if not click_key:
        return False

    key_job = click_key(int(param["android_back_key"])).wait()
    if not key_job.succeeded:
        return False

    time.sleep(float(param["story_page_back_wait"]))
    return True


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


def _find_readable_story_page(
    context: Context,
    param: Dict[str, Any],
) -> Tuple[np.ndarray, list[int]]:
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

    while True:
        now = time.monotonic()
        elapsed = now - started_at
        if elapsed > float(param["max_reading_seconds"]):
            print("Reading loop timed out before returning to story list.")
            return False

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

            if elapsed >= float(param["min_reading_seconds"]) and (
                list_visible or diff <= float(param["return_diff_threshold"])
            ):
                stable_hits += 1
                if stable_hits >= int(param["required_stable_hits"]):
                    if list_visible:
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

            return _read_until_story_list_returns(context, story_list_baseline, param)

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
        image = _screencap(context)
        if _handle_interruptions(context, image, param):
            return False

        story_hit = _recognize(context, str(param["story_home_confirm_node"]), image)
        if not story_hit or not story_hit.box:
            print("No unread story remains after applying the unread filter.")
            return False

        print("Unread filter applied; opening the selected unread story.")
        return _click_box_center(context, story_hit.box)
