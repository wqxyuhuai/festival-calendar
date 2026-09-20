# 每日黄历 · Chinese calendar

每天一个全天事件，过去 7 天 + 今天 + 未来 60 天，共 68 天。标题是「黄历 · 农历日期」，备注包含带 emoji 的农历、干支、宜、忌、值神五个段落。无来源行、无时辰、无提醒；长文字由客户端自然换行。

订阅：https://wqxyuhuai.github.io/festival-calendar/chinese-calendar/daily.ics

## 数据来源与口径

- 数据库与算法：[6tail/lunar-python](https://github.com/6tail/lunar-python)，固定版本 `1.4.8`，MIT 许可。随附 [许可文本](THIRD_PARTY_LICENSE.txt)。生成时不调用网络黄历接口。
- 按北京时间确定当天。干支年使用 `getYearInGanZhiByLiChun()`，以立春所在民用日换年；干支月使用 `getMonthInGanZhi()`，以节令所在民用日换月。它们不是按节气精确时刻切换的八字口径。
- 干支日使用 `getDayInGanZhi()`，每日零点换日；宜忌固定使用 `sect=1`，与上面的月干支口径一致。闰月显示「闰」字。
- 「吉/凶」来自值神体系，不代表所有事项的综合判断。不同通书的宜忌可能不同；本项目保证固定来源与可复现，不承诺与所有应用一致。
- 2026-08-21 样本与用户截图核对：七月初九、丙午年丙申月丁卯日、朱雀黑道凶，宜忌集合一致。
- 农历样本参照香港天文台 [2026 年历表](https://www.hko.gov.hk/en/gts/time/calendar/text/files/T2026e.txt)及 [2025 年历表](https://www.hko.gov.hk/en/gts/time/calendar/text/files/T2025e.txt)，覆盖春节、七月日期和闰六月。样本核对不等同于所有日期的独立认证。

## 文件与更新

- `chinese-calendar/config.json`：订阅名称和前后天数。
- `chinese-calendar/requirements.txt`：固定数据源版本。
- `chinese-calendar/daily.ics`：上次成功生成的订阅。
- `chinese-calendar/snapshot.json`：上次计算的结构化数据、来源版本、生成时间和覆盖范围，仅用于维护。

生成过程先完成全部日期计算，再替换 ICS；失败时保留已有订阅文件。完整发布由 `.github/workflows/publish-calendars.yml` 执行，先测试再生成，再组装 Pages。黄历失败时依然发布上次成功文件和节日，工作流保留失败信号供维护者处理。不要自动升级依赖；升级后先复核样本与生成差异。

ICS 使用 CRLF、UTF-8 按 75 字节折行、日期型全天事件和独占的次日结束日期。每一天的 UID 固定，避免滚动更新生成重复事件。备注仅写入语义换行，不插入缩进空格。刷新周期是客户端提示，无法强制 iOS 即时刷新。

## 指定日期复现

```sh
python chinese-calendar/generate.py --today 2026-09-20 --output-dir _site/sample
```

订阅滚动移除过期记录，不提供永久历史归档。启用后覆盖日期会出现事件标记，可在苹果日历中隐藏此订阅。实际 iPhone 排版和刷新需要在设备上验收。
