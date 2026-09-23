---
name: ia-pinescript
class: language
description: >-
  Pine Script v6: syntax, performance, error diagnosis, backtesting,
  visualization. Use when writing or debugging `.pine` files or TradingView
  Pine indicators/strategies.
paths: "**/*.pine"
---

# Pine Script Development

**Verify before implementing**: For Pine Script version-specific syntax or new built-in functions, look up current docs via Context7 (`query-docs`) before writing code. TradingView updates Pine Script frequently and training data may be stale.

## Critical Syntax Rules

- Keep simple ternaries readable; multiline expressions require valid continuation indentation. For complex ternaries, use intermediate variables:
  ```
  isBull = close > open
  barColor = isBull ? color.green : color.red
  ```
- **Continuation lines outside parentheses MUST be indented by a non-multiple of 4**: same indentation as the start errors, and 4/8/12 spaces parse as a local block and error too (2 spaces is the conventional choice). Inside parentheses (function calls, parenthesized expressions) any indentation works, including multiples of 4
- **NEVER use plot() inside local scopes** (if/for/functions); use conditional value instead: `plot(condition ? value : na)`
- Use `barstate.isconfirmed` when signals require the chart bar's closing values. It does not establish that requested higher-timeframe values are confirmed; inspect `request.security()` offsets and lookahead separately.

## Platform Limits

Check the current [platform limits](https://www.tradingview.com/pine-script-docs/writing/limitations/) before sizing a script: 64 plot counts (one call can consume several); up to 500 line, box, or label IDs each and 100 polyline IDs; 40 unique `request.*()` calls, or 64 on Ultimate; 100,000 compiled tokens. History buffers, requested intrabars, and chart history have distinct limits; there is no general 500-bar `request.security()` history limit.

- Drawings positioned with `xloc.bar_index` reach at most 9,999 bars into the past and 500 into the future; for anything older, switch the drawing to `xloc.bar_time` and pass a timestamp (a time value without `xloc.bar_time` is treated as a future bar index and errors)
- Set the relevant `max_*_count` declaration parameter and cap growth with a rolling buffer: push each object, then `line.delete(arr.shift())` after the intended line count is exceeded. The default display count is approximately 50 per drawing type.

## Performance

- **Tuple security calls**: one `request.security()` returning `[close, high, low]` instead of 3 separate calls
- Pre-allocate arrays with `array.new<type>(size)` instead of push-and-resize
- Short-circuit signals: build conditions incrementally, exit early when first condition fails
- Cache repeated calculations in variables; Pine recalculates every bar
- Iterate collections with `for item in myArray` (or `for [i, item] in myArray`) instead of `for i = 0 to array.size(...) - 1`; the indexed form re-evaluates the bound each pass and breaks when the loop mutates the array's size
- Model related values as a user-defined type, not parallel arrays: `type Trade` with `float entry`, `int startBar`, plus `method` functions, stored in one `array<Trade>`. Parallel arrays (`entries`, `startBars`, ...) desync on any missed push/remove and every operation must be repeated per array; one typed array keeps each object's fields together

## Debugging

Use [Pine Logs](https://www.tradingview.com/pine-script-docs/writing/debugging/) through `log.info()`, `log.warning()`, and `log.error()`, plus these visual checks:

- **Label debugging**: `label.new(bar_index, high, str.tostring(myVar))` to inspect values; cap retained labels explicitly.
- **Table monitor**: `table.new()` with `barstate.islast` for real-time variable dashboard
- **Debug mode toggle**: use `if input.bool(false, "Debug")` for local debug code; keep plot calls global.
- **Repainting checks**: record live signals with timestamps, then compare the same bars after reload. `value[1]` refers to the preceding bar and does not detect revisions to an earlier calculation.

## Strategy & Backtesting

- Use `strategy.*` functions: `strategy.wintrades`, `strategy.losstrades`, `strategy.grossprofit`
- Drawdown tracking: `maxEquity = math.max(strategy.equity, nz(maxEquity[1]))`, then `dd = (maxEquity - strategy.equity) / maxEquity * 100`
- Estimate annualized Sharpe from mean excess returns divided by their standard deviation, scaled by the square root of periods per year; state the sampling interval and annualization assumptions and handle zero variance.
- **Walk-forward validation**: optimize on period 1, test on period 2, re-optimize on period 2, test on period 3. Compare degradation against sampling uncertainty, costs, and regime changes; no universal percentage establishes overfitting.
- **Indicator accuracy testing**: at bar `t`, score `prediction[horizon]` against the now-realized outcome, such as `close > close[horizon]`, excluding warmup bars. Positive offsets reference the past, never future bars; see [history referencing](https://www.tradingview.com/pine-script-docs/language/operators/).
- **Count evaluations per slice**: a slice scored N times during tuning is tuning data, whatever it is labelled, so a multi-parameter sweep run across every slice turns the "validation" numbers into selection bias. Reserve at least one slice with an explicit look budget, spend it after the parameters are locked, and treat "one more look" as the signal to stop
- **Conflicting per-slice optima indicate instability**: compare a robust fixed parameter with a simpler strategy before adding a regime classifier. Fit any classifier using information available before entry and validate it on untouched data; conflicting optima alone do not prove that every fixed parameter fails.
- **Re-run every parameter sweep with the regime gate active**: pre-gate sweeps do not transfer, because losing ungated sessions mask the parameter's real effect. A filter calibrated against one strategy's failure mode does not carry to a sibling on the same signal

## Visualization

- `color.from_gradient()` for trend strength coloring
- Adaptive text sizing: `size.small` for intraday, `size.normal` for daily+
- Dynamic table rows: resize based on enabled features via input toggles
- `input.*(..., active = condition)` greys out an input when its controlling toggle is off (e.g. a smoothing length only editable while "Use smoothing" is checked), which is clearer than a tooltip saying "ignored unless..."
- Professional color constants: define BULL_COLOR, BEAR_COLOR, NEUTRAL_COLOR once with transparency

## Publishing

- Documentation goes at TOP of .pine file as comments before `indicator()`/`strategy()`
- Use `@version`, `@description`, `@param` tags
- Multi-line tooltips: `tooltip="Line 1" + "\n" + "Line 2"`
- Before publishing, consult current TradingView publishing rules for the script's visibility and category; do not infer platform policy from a fixed checklist.

## Common Coding Mistakes

- Indicator stacking (RSI + Stochastics + CCI): all measure the same thing (momentum). Use indicators from different categories instead.
- Assess parameter stability on untouched data; an oddly specific value is not proof of overfitting, and round numbers do not prevent it.
- State whether signals intentionally update intrabar or require confirmed bars; test that behavior, including requested timeframes.
- Hardcoded thresholds without `input()` make the script untestable across instruments.

## Workflow

1. Write indicator/strategy in Pine Editor
2. Test with bar replay and strategy tester on multiple timeframes
3. Walk-forward validate before trusting backtest results (see Strategy & Backtesting above)
4. Verify: run on 3+ symbols and 2+ timeframes

## Verify

- Indicator compiles without errors on TradingView
- Verify signal stability with live/reloaded bar comparisons and inspect higher-timeframe requests; a guard's presence alone is not proof.
- Walk-forward tested on 3+ symbols across different timeframes
