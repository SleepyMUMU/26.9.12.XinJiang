# -*- coding: utf-8 -*-
import os
import json
import datetime
import time
import hashlib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_file_hash(filepath):
    """计算文件的 SHA-256 哈希值，忽略跨平台换行符差异"""
    hasher = hashlib.sha256()
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read().replace('\r\n', '\n')
        hasher.update(content.encode('utf-8'))
    return hasher.hexdigest()

def get_beijing_today():
    """获取北京时间（UTC+8）的今天日期与确切时间"""
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    bj_now = utc_now + datetime.timedelta(hours=8)
    return bj_now.strftime('%Y-%m-%d'), bj_now.strftime('%Y-%m-%d %H:%M:%S')

def migrate_old_history(old_data):
    """将旧格式的数据平滑升级为新版包含哈希的格式"""
    new_data = {
        "file_hashes": {},
        "daily_stats": {}
    }
    if isinstance(old_data, list):
        for item in old_data:
            dt_str = item.get("time", "")
            if dt_str:
                day = dt_str.split(" ")[0]
                new_data["daily_stats"][day] = {
                    "total_completed": item.get("completed", 0),
                    "new_files": [],
                    "strengthened_files": []
                }
    elif isinstance(old_data, dict) and "daily_stats" in old_data:
        new_data = old_data
    return new_data

def main():
    today, now_str = get_beijing_today()

    # 1. 读配置
    config_file = os.path.join(BASE_DIR, 'config.json')
    total_imgs = 0
    project_title = "标注项目进度"
    repository = "SleepyMUMU/26.9.12.XinJiang"
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            total_imgs = config.get('total_images', 0)
            project_title = config.get('project_title', project_title)
            repository = config.get('repository', repository)

    # 2. 读历史
    history_file = os.path.join(BASE_DIR, 'progress_history.json')
    history_data = {"file_hashes": {}, "daily_stats": {}}
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as fh:
                history_data = migrate_old_history(json.load(fh))
        except Exception:
            pass
            
    # 准备当日数据结构
    if today not in history_data["daily_stats"]:
        history_data["daily_stats"][today] = {
            "total_completed": 0,
            "new_files": [],
            "strengthened_files": []
        }
    today_stats = history_data["daily_stats"][today]

    # 3. 扫描所有 json 文件并对比哈希
    files = os.listdir(BASE_DIR)
    current_jsons = []
    for f in files:
        if f.endswith('.json') and f not in ('progress_history.json', 'config.json'):
            current_jsons.append(f)

    completed_labels = len(current_jsons)
    
    # 将 list 转 set，防止重复
    new_set = set(today_stats.get("new_files", []))
    str_set = set(today_stats.get("strengthened_files", []))
    
    hashes = history_data["file_hashes"]
    
    for f in current_jsons:
        f_path = os.path.join(BASE_DIR, f)
        f_hash = get_file_hash(f_path)
        name_only = os.path.splitext(f)[0]
        
        old_hash = hashes.get(f)
        
        if not old_hash:
            # 文件不存在于记录中 -> 新增
            new_set.add(name_only)
        elif old_hash != f_hash:
            # 文件发生改变 -> 加强
            # 如果它在同一天先是被“新增”，然后被“修改”，那它还是应该归类为“新增”
            if name_only not in new_set:
                str_set.add(name_only)
                
        # 更新记录
        hashes[f] = f_hash

    # 清理掉已经被用户在本地删除的冗余哈希记录（虽然少见，但安全第一）
    hashes = {k: v for k, v in hashes.items() if k in current_jsons}
    history_data["file_hashes"] = hashes
    
    # 存回 today_stats
    today_stats["new_files"] = sorted(list(new_set))
    today_stats["strengthened_files"] = sorted(list(str_set))
    today_stats["total_completed"] = completed_labels
    
    # 4. 写入 progress_history.json
    with open(history_file, 'w', encoding='utf-8') as fh:
        json.dump(history_data, fh, ensure_ascii=False, indent=2)

    # 5. 生成 SVG 图表
    days = sorted(history_data["daily_stats"].keys())
    plot_data = []
    for d in days:
        plot_data.append({
            "day": d[5:],
            "completed": history_data["daily_stats"][d].get("total_completed", 0)
        })
    plot_data = plot_data[-12:] if len(plot_data) > 12 else plot_data
    
    width, height = 600, 220
    margin_left, margin_right, margin_top, margin_bottom = 55, 30, 30, 45
    chart_w = width - margin_left - margin_right
    chart_h = height - margin_top - margin_bottom
    
    svg_parts = []
    svg_parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="{height}">'
        '<defs>'
        '  <linearGradient id="grid-grad" x1="0%" y1="0%" x2="0%" y2="100%">'
        '    <stop offset="0%" stop-color="#3b82f6" stop-opacity="0.25" />'
        '    <stop offset="100%" stop-color="#3b82f6" stop-opacity="0.0" />'
        '  </linearGradient>'
        '</defs>'
    )
    
    y_ticks = [0, 20, 40, 60, 80, 100]
    for tick in y_ticks:
        y_val = margin_top + chart_h - (tick / 100.0) * chart_h
        svg_parts.append(
            f'  <line x1="{margin_left}" y1="{y_val}" x2="{width - margin_right}" y2="{y_val}" '
            f'stroke="#e5e7eb" stroke-dasharray="4,4" stroke-width="1" />'
        )
        svg_parts.append(
            f'  <text x="{margin_left - 10}" y="{y_val + 4}" font-family="system-ui, -apple-system, sans-serif" '
            f'font-size="10" fill="#6b7280" text-anchor="end">{tick}%</text>'
        )
        
    if not plot_data:
        svg_parts.append(
            f'  <text x="{width / 2}" y="{height / 2}" font-family="system-ui, -apple-system, sans-serif" '
            f'font-size="14" fill="#9ca3af" text-anchor="middle">暂无数据</text>'
        )
    else:
        points = []
        for idx, pt in enumerate(plot_data):
            comp = pt.get('completed', 0)
            pct = (comp / total_imgs * 100) if total_imgs > 0 else 0
            if len(plot_data) == 1:
                x_val = margin_left + chart_w / 2
            else:
                x_val = margin_left + idx * (chart_w / (len(plot_data) - 1))
            y_val = margin_top + chart_h - (pct / 100.0) * chart_h
            points.append((x_val, y_val, pct, pt['day']))

        if len(points) > 1:
            path_coords = [f"{points[0][0]},{margin_top + chart_h}"]
            for x, y, _, _ in points:
                path_coords.append(f"{x},{y}")
            path_coords.append(f"{points[-1][0]},{margin_top + chart_h}")
            path_str = " ".join(path_coords)
            svg_parts.append(f'  <polygon points="{path_str}" fill="url(#grid-grad)" />')

        poly_coords = " ".join([f"{x},{y}" for x, y, _, _ in points])
        svg_parts.append(
            f'  <polyline points="{poly_coords}" fill="none" stroke="#3b82f6" stroke-width="2.5" '
            f'stroke-linecap="round" stroke-linejoin="round" />'
        )

        for idx, (x, y, pct, day_str) in enumerate(points):
            svg_parts.append(
                f'  <circle cx="{x}" cy="{y}" r="4" fill="#ffffff" stroke="#3b82f6" stroke-width="2" />'
            )
            show_text = True
            if len(points) > 6 and idx % 2 != 0 and idx != len(points) - 1:
                show_text = False
            if show_text:
                svg_parts.append(
                    f'  <text x="{x}" y="{y - 10}" font-family="system-ui, -apple-system, sans-serif" '
                    f'font-size="9" font-weight="bold" fill="#2563eb" text-anchor="middle">{pct:.1f}%</text>'
                )
            svg_parts.append(
                f'  <text x="{x}" y="{margin_top + chart_h + 15}" font-family="system-ui, -apple-system, sans-serif" '
                f'font-size="9" fill="#6b7280" text-anchor="middle">{day_str}</text>'
            )

    svg_parts.append('</svg>')
    
    with open(os.path.join(BASE_DIR, 'progress_chart.svg'), 'w', encoding='utf-8') as f_svg:
        f_svg.write("\n".join(svg_parts))

    # 6. 生成 README
    percent = (completed_labels / total_imgs * 100) if total_imgs > 0 else 0.0
    visual_percent = min(max(percent, 0.0), 100.0)
    bar_length = 20
    filled_length = int(round(bar_length * (visual_percent / 100.0))) if total_imgs > 0 else 0
    bar = '█' * filled_length + '░' * (bar_length - filled_length)
    remaining_imgs = max(0, total_imgs - completed_labels)
    repository_name = repository.rsplit('/', 1)[-1]

    if total_imgs > 0:
        total_value = str(total_imgs)
        total_progress = f"`[{'█' * bar_length}]` 100.0%"
        completed_progress = f"`[{bar}]` {percent:.1f}%"
        remaining_value = str(remaining_imgs)
        remaining_progress = f"`[{'░' * bar_length}]` {max(0.0, 100.0 - percent):.1f}%"
        badge_url = (
            f"https://img.shields.io/badge/Progress-{completed_labels}%20%2F%20{total_imgs}"
            f"%20({percent:.1f}%25)-blue?style=for-the-badge&logo=github"
        )
        setup_notice = ""
    else:
        total_value = "待配置"
        total_progress = "—"
        completed_progress = f"`[{bar}]` 待配置"
        remaining_value = "待配置"
        remaining_progress = "—"
        badge_url = "https://img.shields.io/badge/Progress-Setup_required-orange?style=for-the-badge&logo=github"
        setup_notice = (
            "> [!IMPORTANT]\n"
            "> 请先在 `config.json` 中填写 `total_images`，看板才会计算准确进度。\n\n"
        )
    
    # 构建历史记录面板 (取最近 7 天)
    recent_days = sorted(history_data["daily_stats"].keys(), reverse=True)[:7]
    log_html = "### 📅 每日标注聚合日志\n\n"
    
    for day in recent_days:
        st = history_data["daily_stats"][day]
        d_comp = st.get("total_completed", 0)
        d_pct = (d_comp / total_imgs * 100) if total_imgs > 0 else 0.0
        d_progress = f"{d_comp}/{total_imgs} ({d_pct:.1f}%)" if total_imgs > 0 else f"{d_comp}/待配置"
        n_list = st.get("new_files", [])
        s_list = st.get("strengthened_files", [])
        n_cnt = len(n_list)
        s_cnt = len(s_list)
        
        # 默认今天展开，以前的收起
        open_attr = " open" if day == today else ""
        
        if n_cnt == 0 and s_cnt == 0:
            log_html += f"<details{open_attr}>\n"
            log_html += f"<summary><b>{day}</b> : 进度 {d_progress} | 💤 暂无更新 🔽</summary>\n"
            log_html += f"\n*这一天项目进度发生同步，但无具体标注文件的变更。*\n"
            log_html += "</details>\n\n"
        else:
            log_html += f"<details{open_attr}>\n"
            log_html += f"<summary><b>{day}</b> : 进度 {d_progress} | 🌟 新增 {n_cnt} | 🔨 加强 {s_cnt} 🔽</summary>\n<br>\n"
            
            if n_cnt > 0:
                log_html += f"  <details>\n  <summary>🌟 <b>新增文件 ({n_cnt})</b> 🔽</summary>\n\n"
                log_html += f"  `{'`, `'.join(n_list)}`\n"
                log_html += f"  </details>\n"
            
            if s_cnt > 0:
                log_html += f"  <details>\n  <summary>🔨 <b>加强文件 ({s_cnt})</b> 🔽</summary>\n\n"
                log_html += f"  `{'`, `'.join(s_list)}`\n"
                log_html += f"  </details>\n"
            
            log_html += "</details>\n\n"

    timestamp = int(time.time())

    readme_content = f"""# 🗺️ {project_title} ({repository_name})

> [!NOTE]
> 本仓库仅同步 Labelme 标注所生成的 JSON 数据。图片总数在 `config.json` 中配置，GitHub Actions 会在每次推送时自动统计当前的 JSON 文件数量并更新此看板。

## 🛰️ GPT 辅助判读示意

> [!TIP]
> 下列图片由 GPT 根据遥感影像生成，用于统一高原山地的判读思路。图中的边界和文字均为辅助解释，不是最终标注真值；实际圈画仍应以原始高分辨率影像和项目标准为准。

<p align="center">
  <img src="docs/assets/gpt-remote-sensing-interpretation.png" alt="GPT 生成的遥感影像基础判读示意图" width="820">
</p>

**基础地物判读：** 青色范围表示连续冰雪／冰川覆盖区，可作为 **7 冰雪** 的边界参考；橙色范围表示裸地或岩石山体，通常优先考虑 **11 不可种植区**；蓝色线强调冰川槽谷／冰川舌的形态。黄色虚线标出的“侧碛（可能）”是辅助识别冰川地貌的线索，本身不是独立标签，不能仅凭该线索直接定类。

<p align="center">
  <img src="docs/assets/gpt-planting-suitability.png" alt="GPT 生成的高原山地种草种树粗略判读图" width="820">
</p>

**种植适宜性初判：** 绿色范围表示相对平缓、可能具有一定土层的 **可种草优先区**，可作为 **8 裸地种草区** 的候选；深青色小范围表示条件较好的 **可种树候选区**，对应 **9 裸地种树区**；橙色陡坡、沟谷、裸岩和积雪高山属于 **不建议种植区**，通常对应 **11 不可种植区**。

- 图中的颜色只表达本示意图的判读分区，不应套用为整个项目的固定显示颜色。
- **8、9、10 类属于适宜性判断**，仅凭一张自然色影像无法可靠定论；还应结合坡度、水源、土层厚度、盐碱度、已有植被和现场资料。
- 对边界模糊、阴影遮挡或无法确认的区域应保守圈画，避免为了填满画面而强行赋予标签。

---

{setup_notice}### 📊 标注状态看板

| 统计项 | 数值 | 占比 / 进度条 |
| :--- | :---: | :--- |
| **总图片数 (Total)** | **{total_value}** | {total_progress} |
| **已标记 (Completed)** | **{completed_labels}** | {completed_progress} |
| **未标记 (Remaining)** | **{remaining_value}** | {remaining_progress} |

**当前总体进度：**
![Progress Badge]({badge_url})

### 📈 标注进度趋势折线图
![标注进度趋势](https://raw.githubusercontent.com/{repository}/assets/progress_chart.svg?v={timestamp})

---
{log_html}
---
*📅 统计更新时间：{now_str} (UTC+8)*

---
## 👥 多人协作说明
本项目已全面接入 **GitHub Actions**。作为协作者，您**无需**在本地运行任何脚本或配置任何 Git 钩子。
只要您正常将 `.json` 文件 `git push` 到仓库，云端就会自动计算并更新此 README 文件和趋势图！
（如果您向本地库新增了待标注图片，请顺手修改 `config.json` 中的 `total_images` 数值即可。）
"""
    with open(os.path.join(BASE_DIR, 'README.md'), 'w', encoding='utf-8') as fr:
        fr.write(readme_content)

if __name__ == '__main__':
    main()
