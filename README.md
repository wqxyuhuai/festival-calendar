# 苹果日历补充订阅

两个独立订阅：节日补充与每日黄历（Chinese calendar）。可以单独订阅，也可以同时使用。

| 日历 | 订阅地址 |
| --- | --- |
| 节日补充 | https://wqxyuhuai.github.io/festival-calendar/festival_extra.ics |
| 每日黄历 | https://wqxyuhuai.github.io/festival-calendar/chinese-calendar/daily.ics |

原节日订阅地址永久保留，已订阅用户无需重新添加。请以「订阅日历」方式添加，下载导入不能持续更新。

## 目录

```text
proj-festivals/            节日数据、生成器、订阅文件
proj-chinese-calendar/     黄历配置、生成器、订阅文件和数据快照
doc-festivals/             节日文档与订阅页面
doc-chinese-calendar/      黄历文档与订阅页面
scripts/                  共用网站组装工具
tests/                    日期、ICS 与发布兼容性测试
.github/workflows/        自动生成与 GitHub Pages 发布
```

- [节日维护说明](doc-festivals/README.md)
- [黄历数据与维护说明](doc-chinese-calendar/README.md)

## 生成与检查

需要 Python 3.12：

```sh
python -m pip install -r proj-chinese-calendar/requirements.txt
python proj-festivals/generate.py
python -m unittest discover -s tests -v
python proj-chinese-calendar/generate.py
python scripts/build_site.py
```

`_site/` 为临时发布目录，不提交到仓库。GitHub Pages 的构建来源设置为 **GitHub Actions**。发布流程每天北京时间 03:17 定时运行，也可手动触发；GitHub 定时任务可能延迟。公开仓库长期无活动时 GitHub 可能暂停定时任务，需留意 Actions 状态。

节日源数据没有变化时不重写订阅文件。发布脚本将其原样复制到网站根目录的 `festival_extra.ics`。黄历失败时使用上次成功版本，并让工作流报告失败；节日仍可发布。关注失败通知，避免保留版本超过未来 60 天的覆盖范围。
