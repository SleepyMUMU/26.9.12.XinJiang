# 标注仓库同步模板

main 保存 JSON、说明和自动化脚本；assets 保存 SVG 与 GPT 示例图。README 使用远程图片地址，浏览网页时才加载图片。

## 新电脑克隆（不下载旧历史图片或 assets）

```powershell
git clone --filter=blob:none --depth 1 --single-branch --branch main https://github.com/SleepyMUMU/26.9.12.XinJiang.git
```

普通完整 clone 仍可能下载旧提交里的图片，.gitignore 不会清除历史。

## 每次标注

原始图片保存在本地，使用 `labelme --nodata` 启动（或将 Labelme 配置的 store_data 设为 false）。
提交之前运行 `python strip_image_data.py`；只清除 imageData，其他标注字段不变。
运行 `python strip_image_data.py --check` 检查后再提交 JSON。云端也会检查，发现内嵌图片会阻止看板更新，但无法撤销已上传的提交，所以必须在提交前清理。
图片路径仍用于读取本地原图；协作者需要自行准备同名原图。

## 新地区或下一批标签复用

复制 .gitignore、.github/workflows/update_progress.yml、update_readme.py、strip_image_data.py、SYNC.md。
创建 config.json：repository 填新仓库 owner/name，project_title 填标题，total_images 填总数。
不要复制旧项目的 progress_history.json 和标注 JSON；脚本会生成新的历史。
README 中 GPT 示例说明针对新疆山地，新项目应按实际标签修改 update_readme.py 中对应段落。
如需保留 GPT 示例图，先将所需文件放到新仓库 assets 分支 docs/assets/ 下；不需要时移除脚本中的示例说明段落。
推送 main 后自动更新，也可通过 Actions 的 workflow_dispatch 手动执行。此处“标签”指业务标注；Git tag 不触发写回 main。

## 已有本地仓库只拉取 main

```powershell
git config --replace-all remote.origin.fetch '+refs/heads/main:refs/remotes/origin/main'
git config remote.origin.tagOpt --no-tags
git pull --ff-only
```

这不删除本地原图或已经存在的历史对象。勿使用 git add -f 上传图片。
