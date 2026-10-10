# Robot Log Analyzer

A Python program that reads voltage and current data from a CSV file, groups unusual readings into events, and prints summaries.

I built this project to practice working with robot logs, detecting problems, and measuring how well different detection methods perform.

## Features

- Read timestamps, voltage, and current from a CSV file.
- Detect low voltage and high current using fixed thresholds.
- Detect unusual changes using recent readings as a baseline.
- Summarize each event with its start time, end time, sample count, and minimum voltage or maximum current.
- Compare detections with labeled events using precision, recall, and F1.

## Project Files

| File | Purpose |
|---|---|
| `main.py` | Selects the mode, settings, and data files. |
| `core.py` | Reads data, detects events, and prints summaries. |
| `benchmark.py` | Scores detections and provides an artificial test example. |
| `Data/sampleData.csv` | Contains the readings to analyze. |
| `Data/sampleLabels.json` | Contains known events for benchmarking a CSV. |

The labels file is only needed for CSV benchmarking.

## Requirements

Python 3. No additional packages are required.

## Running the Program

Open a terminal in the project folder and run:

```bash
python main.py
```

Change the settings inside `main()` in `main.py` to choose what runs.

### Analyze a CSV

```python
mode = "analyze"
method = "fixed"
```

The default fixed thresholds are:

```python
voltageThreshold = 7.0
currentThreshold = 110.0
```

Voltage below 7.0 V is flagged. Current above 110.0 A is flagged. Readings equal to a threshold are not flagged.

To use adaptive detection:

```python
mode = "analyze"
method = "adaptive"
```

### Run the Artificial Example

```python
mode = "demoBenchmark"
```

This creates sample readings inside the program and compares both detection methods against two known events. It does not read the CSV or labels file.

Expected results for each method:

- 2 correct alerts
- 0 false alerts
- 0 missed events
- Precision, recall, and F1 of 1.0

This example checks basic functionality. It does not establish performance on real robot data.

### Benchmark a CSV

```python
mode = "benchmark"
```

This compares both fixed and adaptive detection against the events in `Data/sampleLabels.json`.

The `method` setting only affects analysis mode. Benchmark mode runs both methods.

## CSV Format

The CSV must use these headers:

```csv
timestamp_s,voltage_v,current_a
0.0,1.6,28.2
0.1,12.5,31.0
0.2,10.8,112.0
0.3,12.4,
```

- Timestamps are in seconds and must increase with every row.
- Voltage is in volts.
- Current is in amps.
- Blank voltage or current readings become `None`.
- Timestamps cannot be blank.
- Numeric values must be finite.

With fixed detection, this example produces:

```text
Voltage events:
From 0.0s to 0.0s: lowest voltage was 1.6 V (1 samples, observed duration 0.0s)

Current events:
From 0.2s to 0.2s: highest current was 112.0 A (1 samples, observed duration 0.0s)
```

The default CSV path is `Data/sampleData.csv`. If your file has a different name, update `dataPath` in `main.py`.

## How Detection Works

### Fixed Detection

Fixed detection compares each reading with a set threshold.

Consecutive flagged readings form one event. A normal or missing reading for that signal ends the event.

### Adaptive Detection

Adaptive detection compares each reading with valid readings from the previous three seconds.

It uses their median as a baseline and their median absolute deviation to estimate normal variation.

An event is flagged when:

- Voltage drops far enough below its recent baseline.
- Current rises far enough above its recent baseline.

The detector requires at least five previous valid readings within the time window. It therefore cannot flag the first few readings.

The minimum change is 0.35 V for voltage and 15 A for current. Noisier readings can increase the change required to trigger an event.

Adaptive settings are defined in `groupAdaptive()` in `core.py`.

## Event Labels

Labels describe known events identified independently of the detector.

For the four-row CSV above, the labels would be:

```json
[
    {
        "signal": "voltageV",
        "startS": 0.0,
        "endS": 0.1
    },
    {
        "signal": "currentA",
        "startS": 0.2,
        "endS": 0.3
    }
]
```

Each interval includes its start and excludes its end. For scoring, a reading represents one sampling interval.

Replace these labels when using a different CSV. Include all events you intend to evaluate; an unlabeled detection is counted as a false alert.

## Benchmark Scores

The benchmark matches predictions and labels for the same signal using Intersection over Union (IoU), which measures their overlap.

The default minimum IoU is 0.1. Matches are chosen by strongest overlap, and each prediction and label can be matched only once.

| Metric | Meaning |
|---|---|
| True positives | Detected events matched to known events. |
| False positives | Detected events without a match. |
| False negatives | Known events that were missed. |
| Precision | Fraction of detected events that matched known events. |
| Recall | Fraction of known events that were detected. |
| F1 | Combined score balancing precision and recall. |

Scores are combined across voltage and current events.

## Current Limitations

- CSV benchmarking requires evenly spaced timestamps.
- Printed duration is the time between the first and last flagged readings. A single-sample event has an observed duration of zero.
- Benchmark scoring extends an event through one sampling interval after its last flagged reading.
- Missing readings end an event for that signal but are not reported as separate events.
- Adaptive detection includes unusual readings in its history, so it can eventually adapt to a sustained fault.
- Event grouping follows consecutive rows and does not separately split events at large timestamp gaps.
- Reliable performance measurements require representative logs with independently checked labels.

## Possible Next Steps

- Test with longer robot logs.
- Add labeled examples with noise, missing readings, and sustained faults.
- Export event summaries to a file.
- Plot voltage and current with detected events highlighted.
- Compare settings using separate development and evaluation data.