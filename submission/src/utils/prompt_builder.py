"""Prompt construction for single-step GUI decisions."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from .image_utils import encode_image_url


class PromptBuilder:
    def build(self, input_data, memory, task_slots) -> List[Dict[str, Any]]:
        recent = memory.recent_actions(5)
        slot_text = {
            "app_name": task_slots.app_name,
            "task_type": task_slots.task_type,
            "shop": task_slots.shop,
            "product": task_slots.product,
            "origin": task_slots.origin,
            "destination": task_slots.destination,
            "query_candidates": task_slots.query_candidates,
        }

        history_actions = input_data.history_actions[-6:] if getattr(input_data, "history_actions", None) else []
        candidate_text = self._format_candidates(getattr(memory, "last_candidates", []))

        prompt = f"""你是一个移动端 GUI Agent。你需要根据当前手机截图、用户任务和历史动作，决定下一步唯一操作。

用户任务：
{input_data.instruction}

当前步数：{input_data.step_count}

已解析任务槽位：
{slot_text}

最近历史动作：
{recent}

评测器历史动作：
{history_actions}

当前可点击候选元素：
{candidate_text}

你只能输出下面五种动作之一：
{{"action":"CLICK","target_id":候选元素id}}
{{"action":"CLICK","point":[x,y]}}
{{"action":"TYPE","text":"要输入的文字"}}
{{"action":"SCROLL","start_point":[x1,y1],"end_point":[x2,y2]}}
{{"action":"OPEN","app_name":"应用名"}}
{{"action":"COMPLETE"}}

重要规则：
1. 坐标必须是 0 到 1000 的归一化坐标，点击时选控件中心，不要给真实像素坐标。
2. CLICK 必须优先从“当前可点击候选元素”中选择 target_id；只有候选元素明显没有目标控件时，才允许输出 point。
3. 不要把 target_id 当坐标；target_id 只是候选元素 id，程序会自动点击该元素中心。
4. 先判断当前页面属于哪一步：桌面、App 首页、搜索页、搜索结果、详情页、表单页、弹窗、已完成页。
5. 如果当前截图还在桌面，并且任务指定了 App，输出 {{"action":"OPEN","app_name":"..."}}。
6. 如果搜索框、输入框或评论框已经获得焦点，下一步通常是 {{"action":"TYPE","text":"..."}}。
7. TYPE 只输出真正要输入的文字，优先使用“已解析任务槽位”中的搜索词、店铺名、商品名、起点、终点或评论内容。
8. 如果刚执行过 type，下一步通常点击“搜索 / 确认 / 发送 / 完成 / 键盘搜索”按钮，优先用对应候选元素 target_id。
9. 如果任务是评价、晒单、评论、发表感受，优先点击“评价 / 去评价 / 评价晒单 / 写评价 / 发表评论 / 发布 / 发送 / 提交”等明确按钮；不要因为页面有列表就先 scroll。
10. 刚输入评价或评论后，不要点右上角搜索/完成图标；社交评论应点右下角发送，电商评价无明确发布按钮时直接 complete。
11. 如果出现权限、广告、青少年模式、升级、弹窗，优先点击关闭、跳过、取消或允许继续任务的按钮。
12. 不要重复点击最近历史里连续点过的位置。
13. 只有已经达到用户任务目标后才 complete；搜索结果页、详情页、输入后未发送都不能提前 complete。
14. 如果目标控件当前屏幕不可见，才使用 scroll；首屏已有可点击目标时不要 scroll。

常见任务思路：
- 搜索/播放/收藏/点赞类：打开 App -> 找搜索入口 -> 输入搜索词 -> 点搜索 -> 打开目标结果 -> 执行收藏/点赞/播放等目标动作。
- 评论类：先找到目标视频或内容 -> 打开评论区 -> 点击评论输入框 -> 输入评论文字 -> 点击发送 -> complete。
- 电商评价类：进入订单或商品评价入口 -> 选择商品/评分 -> 点击评价输入框 -> 输入评价文字 -> 京东/拼多多/淘宝这类电商评价如果没有明确发布按钮，输入完成后通常 complete；如果按钮清楚写着发布/提交/发送才点击。
- 社交/视频评论类：找到目标内容 -> 打开评论区 -> 点击评论输入框 -> 输入评论文字 -> 必须点击右下角发送/发布按钮 -> complete，不要在输入后直接滚动。
- 短视频商品评价/表单评价类：如果前面已经点了星级并在大文本框输入评价，发布/提交按钮常在底部居中，不要误点普通评论框右下角。
- 地图/打车/导航类：按页面提示依次填写起点、终点或目的地 -> 选择候选地址 -> 点击打车/导航/确认。
- 外卖/购物类：进入外卖或购物入口 -> 搜索店铺或商品 -> 打开目标 -> 加入购物车/购买 -> 提交到确认页后 complete。
- 旅行/酒店/机票类：进入对应入口 -> 填出发地、目的地、日期或地点 -> 点击查询 -> 根据任务选择筛选或结果。

输出格式必须是两行，第二行必须以 Action: 开头，Action 后面必须是一个 JSON 对象，不要输出 Markdown 代码块：
Thought: 用中文简短说明当前页面和下一步目标。
Action: {{"action":"CLICK","target_id":7}}"""

        return [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": encode_image_url(input_data.current_image)},
                    },
                ],
            }
        ]

    @staticmethod
    def _format_candidates(candidates) -> str:
        values = []
        for candidate in candidates or []:
            if hasattr(candidate, "to_dict"):
                data = candidate.to_dict()
            elif isinstance(candidate, dict):
                data = candidate
            else:
                data = {"element_id": "", "kind": str(candidate), "center": [], "hint": "", "score": 0.0}
            values.append(
                {
                    "id": data.get("element_id"),
                    "kind": data.get("kind"),
                    "center": data.get("center"),
                    "hint": data.get("hint"),
                    "score": data.get("score", 0.0),
                }
            )
        if not values:
            return "[]"
        return json.dumps(values, ensure_ascii=False)
