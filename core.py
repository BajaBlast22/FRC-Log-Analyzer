import csv
import math
import statistics


# Convert a reading to a number.
# Empty readings become None.
def toFloatOrNone(value):
    if value is None:
        return None

    value = value.strip()

    if value == "":
        return None

    number = float(value)

    if not math.isfinite(number):
        raise ValueError("Readings must be finite numbers.")

    return number

# Read the CSV and create a list of sample dictionaries.
def readLog(path):
    samples = []

    with open(path, newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        requiredColumns = [
            "timestamp_s",
            "voltage_v",
            "current_a"
        ]

        if reader.fieldnames is None:
            raise ValueError("The CSV file has no header.")

        for column in requiredColumns:
            if column not in reader.fieldnames:
                raise ValueError("Missing CSV column: " + column)

        for row in reader:
            timestampS = toFloatOrNone(row["timestamp_s"])
            voltageV = toFloatOrNone(row["voltage_v"])
            currentA = toFloatOrNone(row["current_a"])

            if timestampS is None:
                raise ValueError("A sample is missing its timestamp.")

            if len(samples) > 0:
                previousTime = samples[-1]["timestampS"]

                if timestampS <= previousTime:
                    raise ValueError(
                        "Each timestamp must be greater than the previous one."
                    )

            sample = {
                "timestampS": timestampS,
                "voltageV": voltageV,
                "currentA": currentA
            }

            samples.append(sample)

    if len(samples) == 0:
        raise ValueError("The CSV file contains no samples.")

    return samples


# Find individual low-voltage samples.
def findLowVoltage(samples, threshold=7.0):
    lowVoltageSamples = []

    for sample in samples:
        voltage = sample["voltageV"]

        if voltage is not None and voltage < threshold:
            lowVoltageSamples.append(sample)

    return lowVoltageSamples


# Group consecutive low-voltage samples into events.
def groupLowVoltage(samples, threshold=7.0):
    events = []
    currentEvent = []

    for sample in samples:
        voltage = sample["voltageV"]

        if voltage is not None and voltage < threshold:
            currentEvent.append(sample)

        elif currentEvent:
            events.append(currentEvent)
            currentEvent = []

    # Save an event that continues to the end of the log.
    if currentEvent:
        events.append(currentEvent)

    return events


# Find individual high-current samples.
def findHighCurrent(samples, threshold=110.0):
    highCurrentSamples = []

    for sample in samples:
        current = sample["currentA"]

        if current is not None and current > threshold:
            highCurrentSamples.append(sample)

    return highCurrentSamples


# Group consecutive high-current samples into events.
def groupHighCurrent(samples, threshold=110.0):
    events = []
    currentEvent = []

    for sample in samples:
        current = sample["currentA"]

        if current is not None and current > threshold:
            currentEvent.append(sample)

        elif currentEvent:
            events.append(currentEvent)
            currentEvent = []

    # Save an event that continues to the end of the log.
    if currentEvent:
        events.append(currentEvent)

    return events


# Summarize one voltage or current event.
def summarizeEvent(event, signal):
    if signal not in ["voltageV", "currentA"]:
        raise ValueError("Unknown signal: " + signal)

    if len(event) == 0:
        raise ValueError("Cannot summarize an empty event.")

    startTime = event[0]["timestampS"]
    endTime = event[-1]["timestampS"]

    values = []

    for sample in event:
        value = sample[signal]

        if value is not None:
            values.append(value)

    if len(values) == 0:
        raise ValueError("The event has no readings for " + signal)

    duration = endTime - startTime
    sampleCount = len(event)

    summary = {
        "startS": startTime,
        "endS": endTime,
        "durationS": duration,
        "sampleCount": sampleCount
    }

    if signal == "voltageV":
        summary["minVoltageV"] = min(values)

    elif signal == "currentA":
        summary["maxCurrentA"] = max(values)

    return summary


# Summarize every event in a list.
def summarizeEvents(events, signal):
    summaries = []

    for event in events:
        summary = summarizeEvent(event, signal)
        summaries.append(summary)

    return summaries


# Print readable summaries.
def printSummaries(summaries, signal):
    if signal == "voltageV":
        valueKey = "minVoltageV"
        label = "lowest voltage"
        unit = "V"

    elif signal == "currentA":
        valueKey = "maxCurrentA"
        label = "highest current"
        unit = "A"

    else:
        raise ValueError("Unknown signal: " + signal)

    if len(summaries) == 0:
        print("No events found.")
        return

    for summary in summaries:
        value = summary[valueKey]

        # Round only the displayed times.
        startTime = round(summary["startS"], 3)
        endTime = round(summary["endS"], 3)
        duration = round(summary["durationS"], 3)

        message = (
            "From " + str(startTime)
            + "s to " + str(endTime)
            + "s: " + label + " was "
            + str(value) + " " + unit
            + " (" + str(summary["sampleCount"])
            + " samples, observed duration "
            + str(duration) + "s)"
        )

        print(message)


def analyzeLog(
    path,
    voltageThreshold=7.0,
    currentThreshold=110.0,
    method="fixed"
):
    samples = readLog(path)

    if method == "fixed":
        voltageEvents = groupLowVoltage(samples, voltageThreshold)
        currentEvents = groupHighCurrent(samples, currentThreshold)

    elif method == "adaptive":
        voltageEvents = groupAdaptive(samples, "voltageV")
        currentEvents = groupAdaptive(samples, "currentA")

    else:
        raise ValueError("Method must be fixed or adaptive.")

    voltageSummaries = summarizeEvents(voltageEvents, "voltageV")
    currentSummaries = summarizeEvents(currentEvents, "currentA")

    print("Analyzing: " + str(path))
    print("Method: " + method)
    print("Samples read: " + str(len(samples)))
    print()

    print("Voltage events:")
    printSummaries(voltageSummaries, "voltageV")
    print()

    print("Current events:")
    printSummaries(currentSummaries, "currentA")

    return {
        "voltageSummaries": voltageSummaries,
        "currentSummaries": currentSummaries
    }


def groupAdaptive(
    samples,
    signal,
    windowS=3.0,
    zThreshold=6.0
):
    if signal == "voltageV":
        minimumChange = 0.35

    elif signal == "currentA":
        minimumChange = 15.0

    else:
        raise ValueError("Unknown signal: " + signal)

    if not math.isfinite(windowS) or windowS <= 0:
        raise ValueError("The time window must be finite and positive.")

    if not math.isfinite(zThreshold) or zThreshold <= 0:
        raise ValueError("The sensitivity setting must be finite and positive.")

    events = []
    currentEvent = []
    history = []

    for sample in samples:
        currentTime = sample["timestampS"]
        currentValue = sample[signal]

        # Keep only readings inside the trailing time window.
        recentHistory = []

        for previousSample in history:
            previousTime = previousSample["timestampS"]

            if previousTime >= currentTime - windowS:
                recentHistory.append(previousSample)

        history = recentHistory
        isUnusual = False

        # Wait for at least five previous valid readings.
        if currentValue is not None and len(history) >= 5:
            previousValues = []

            for previousSample in history:
                previousValues.append(previousSample[signal])

            baseline = statistics.median(previousValues)

            # Find how far previous readings usually sit
            # from the baseline.
            deviations = []

            for previousValue in previousValues:
                difference = abs(previousValue - baseline)
                deviations.append(difference)

            medianDeviation = statistics.median(deviations)

            # This converts the median deviation into a
            # conventional robust estimate of variation.
            usualVariation = medianDeviation * 1.4826

            allowedChange = max(
                minimumChange,
                zThreshold * usualVariation
            )

            if signal == "voltageV":
                drop = baseline - currentValue
                isUnusual = drop > allowedChange

            elif signal == "currentA":
                increase = currentValue - baseline
                isUnusual = increase > allowedChange

        if isUnusual:
            currentEvent.append(sample)

        elif currentEvent:
            events.append(currentEvent)
            currentEvent = []

        # Add this reading after checking it, so it does
        # not influence its own baseline.
        if currentValue is not None:
            history.append(sample)

    if currentEvent:
        events.append(currentEvent)

    return events