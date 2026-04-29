"""Prompt construction for single-step GUI decisions."""

from __future__ import annotations

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

你只能输出下面五种动作之一：
click(point='<point>x y</point>')
type(content='要输入的文字')
scroll(start_point='<point>x1 y1</point>', end_point='<point>x2 y2</point>')
open(app_name='应用名')
complete(content='')

重要规则：
1. 坐标必须是 0 到 1000 的归一化坐标，点击时选控件中心，不要给真实像素坐标。
2. 先判断当前页面属于哪一步：桌面、App 首页、搜索页、搜索结果、详情页、表单页、弹窗、已完成页。
3. 如果当前截图还在桌面，并且任务指定了 App，输出 open(app_name='...')。
4. 如果搜索框、输入框或评论框已经获得焦点，下一步通常是 type(content='...')。
5. TYPE 只输出真正要输入的文字，优先使用“已解析任务槽位”中的搜索词、店铺名、商品名、起点、终点或评论内容。
6. 如果刚执行过 type，下一步通常点击“搜索 / 确认 / 发送 / 完成 / 键盘搜索”按钮。
7. 如果目标控件当前屏幕不可见，优先 scroll，而不是乱点。
8. 如果出现权限、广告、青少年模式、升级、弹窗，优先点击关闭、跳过、取消或允许继续任务的按钮。
9. 不要重复点击最近历史里连续点过的位置。
10. 只有已经达到用户任务目标后才 complete；搜索结果页、详情页、输入后未发送都不能提前 complete。

常见任务思路：
- 搜索/播放/收藏/点赞类：打开 App -> 找搜索入口 -> 输入搜索词 -> 点搜索 -> 打开目标结果 -> 执行收藏/点赞/播放等目标动作。
- 评论类：先找到目标视频或内容 -> 打开评论区 -> 点击评论输入框 -> 输入评论文字 -> 点击发送 -> complete。
- 地图/打车/导航类：按页面提示依次填写起点、终点或目的地 -> 选择候选地址 -> 点击打车/导航/确认。
- 外卖/购物类：进入外卖或购物入口 -> 搜索店铺或商品 -> 打开目标 -> 加入购物车/购买 -> 提交到确认页后 complete。
- 旅行/酒店/机票类：进入对应入口 -> 填出发地、目的地、日期或地点 -> 点击查询 -> 根据任务选择筛选或结果。

输出格式必须是两行，第二行必须以 Action: 开头：
Thought: 用中文简短说明当前页面和下一步目标。
Action: click(point='<point>500 500</point>')"""

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
