# 节日补充日历｜Festival Supplement Calendar

这是一个给 Apple Calendar / iPhone 日历订阅用的节日补充日历。

设计目的：

- 保留苹果自带「中国节假日」日历，用来显示放假、调休、补班。
- 额外订阅本日历，用来补充元宵、七夕、重阳、圣诞、情人节等节日。
- 不包含二十四节气、调休、补班。

## Apple Calendar 订阅链接

```text
https://wqxyuhuai.github.io/festival-calendar/festival_extra.ics
```

## 文件结构

```text
data/festivals.csv              # 平时只需要维护这个表格
scripts/generate_ics.py          # 自动把 CSV 生成 .ics，不常改
docs/festival_extra.ics          # 苹果日历订阅的文件，由脚本生成
.github/workflows/build-calendar.yml  # GitHub Actions 自动生成配置
```

## CSV 字段说明

| 字段 | 示例 | 说明 |
|---|---|---|
| enabled | TRUE | 是否启用，FALSE 会被忽略 |
| id | valentine | 唯一 ID，只用英文、数字、下划线、连字符 |
| name | 情人节 | 日历里显示的名称 |
| date | 2026-02-14 | 日期，必须是 YYYY-MM-DD |
| repeat | yearly | `yearly` 每年重复，`none` 只出现一次，`rrule` 使用自定义规则 |
| rrule | FREQ=YEARLY;BYMONTH=5;BYDAY=2SU | 只有 repeat=rrule 时填写 |
| category | international | 分类，仅用于备注 |
| note | 公历固定节日 | 备注，会写入 DESCRIPTION |

## 常见维护方式

### 1. 新增一个公历固定节日

```csv
enabled,id,name,date,repeat,rrule,category,note
TRUE,example-day,示例节日,2026-05-20,yearly,,modern,每年5月20日
```

### 2. 新增一个农历节日

农历节日不要用 yearly，因为每年对应公历日期不同。建议每年写一条：

```csv
TRUE,lantern-lunar2036,元宵节,2036-02-11,none,,lunar,农历正月十五
```

### 3. 暂时隐藏一个节日

把 enabled 改成 FALSE 即可：

```csv
FALSE,valentine,情人节,2026-02-14,yearly,,international,公历固定节日；每年重复
```

## 生成方式

GitHub Actions 会在 `data/festivals.csv` 被修改后自动运行：

```text
CSV 更新
↓
自动运行 scripts/generate_ics.py
↓
自动更新 docs/festival_extra.ics
```

如需手动生成，也可以运行：

```bash
python scripts/generate_ics.py
```



