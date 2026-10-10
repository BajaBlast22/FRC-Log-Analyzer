import math
import statistics

from core import (
    groupLowVoltage,
    groupHighCurrent,
    groupAdaptive
)


# Check that samples are evenly spaced.
def getSamplingInterval(samples):
    if len(samples) < 2:
        raise ValueError("Benchmarking requires at least two samples.")

    intervals = []

    for index in range(1, len(samples)):
        previousTime = samples[index - 1]["timestampS"]
        currentTime = samples[index]["timestampS"]

        interval = currentTime - previousTime

        if not math.isfinite(interval) or interval <= 0:
            raise ValueError("Timestamps must be finite and increasing.")

        intervals.append(interval)

    samplingInterval = statistics.median(intervals)

    for interval in intervals:
        difference = abs(interval - samplingInterval)
        tolerance = max(0.000000001, samplingInterval * 0.000001)

        if difference > tolerance:
            raise ValueError(
                "This benchmark version requires evenly spaced samples."
            )

    return samplingInterval


# Convert groups of samples into time intervals for scoring.
def makeBenchmarkEvents(events, signal, samplingInterval):
    benchmarkEvents = []

    for event in events:
        benchmarkEvent = {
            "signal": signal,
            "startS": event[0]["timestampS"],
            "endS": event[-1]["timestampS"] + samplingInterval
        }

        benchmarkEvents.append(benchmarkEvent)

    return benchmarkEvents


# Intersection over Union measures how much two intervals overlap.
def getEventIou(predictedEvent, actualEvent):
    overlapStart = max(
        predictedEvent["startS"],
        actualEvent["startS"]
    )

    overlapEnd = min(
        predictedEvent["endS"],
        actualEvent["endS"]
    )

    overlapDuration = max(0.0, overlapEnd - overlapStart)

    predictedDuration = (
        predictedEvent["endS"] - predictedEvent["startS"]
    )

    actualDuration = (
        actualEvent["endS"] - actualEvent["startS"]
    )

    unionDuration = (
        predictedDuration + actualDuration - overlapDuration
    )

    if unionDuration <= 0:
        return 0.0

    return overlapDuration / unionDuration


# Match detected events with known events.
def evaluateEvents(predictions, truthEvents, minimumIou=0.1):
    if not (minimumIou > 0 and minimumIou <= 1):
        raise ValueError("Minimum IoU must be greater than 0 and at most 1.")

    for eventList in [predictions, truthEvents]:
        for event in eventList:
            if event["signal"] not in ["voltageV", "currentA"]:
                raise ValueError("Unknown event signal.")

            if not math.isfinite(event["startS"]):
                raise ValueError("Event times must be finite.")

            if not math.isfinite(event["endS"]):
                raise ValueError("Event times must be finite.")

            if event["endS"] <= event["startS"]:
                raise ValueError("Each event must have positive duration.")

    usedPredictions = []
    usedTruth = []

    # Repeatedly choose the strongest remaining match.
    # Each prediction and label can be used only once.
    while True:
        bestPredictionIndex = None
        bestTruthIndex = None
        bestIou = 0.0

        for predictionIndex in range(len(predictions)):
            if predictionIndex in usedPredictions:
                continue

            prediction = predictions[predictionIndex]

            for truthIndex in range(len(truthEvents)):
                if truthIndex in usedTruth:
                    continue

                actualEvent = truthEvents[truthIndex]

                if prediction["signal"] != actualEvent["signal"]:
                    continue

                overlap = getEventIou(prediction, actualEvent)

                if overlap >= minimumIou and overlap > bestIou:
                    bestIou = overlap
                    bestPredictionIndex = predictionIndex
                    bestTruthIndex = truthIndex

        if bestPredictionIndex is None:
            break

        usedPredictions.append(bestPredictionIndex)
        usedTruth.append(bestTruthIndex)

    truePositives = len(usedPredictions)
    falsePositives = len(predictions) - truePositives
    falseNegatives = len(truthEvents) - len(usedTruth)

    precision = 0.0
    recall = 0.0
    f1 = 0.0

    if truePositives + falsePositives > 0:
        precision = truePositives / (
            truePositives + falsePositives
        )

    if truePositives + falseNegatives > 0:
        recall = truePositives / (
            truePositives + falseNegatives
        )

    if precision + recall > 0:
        f1 = 2 * precision * recall / (precision + recall)

    return {
        "truePositives": truePositives,
        "falsePositives": falsePositives,
        "falseNegatives": falseNegatives,
        "precision": precision,
        "recall": recall,
        "f1": f1
    }


# Compare fixed and adaptive detection using the same log and labels.
def benchmark(
    samples,
    truthEvents,
    voltageThreshold=7.0,
    currentThreshold=110.0
):
    samplingInterval = getSamplingInterval(samples)
    results = {}

    for method in ["fixed", "adaptive"]:
        if method == "fixed":
            voltageEvents = groupLowVoltage(
                samples, voltageThreshold
            )

            currentEvents = groupHighCurrent(
                samples, currentThreshold
            )

        else:
            voltageEvents = groupAdaptive(samples, "voltageV")
            currentEvents = groupAdaptive(samples, "currentA")

        voltagePredictions = makeBenchmarkEvents(
            voltageEvents, "voltageV", samplingInterval
        )

        currentPredictions = makeBenchmarkEvents(
            currentEvents, "currentA", samplingInterval
        )

        predictions = voltagePredictions + currentPredictions
        result = evaluateEvents(predictions, truthEvents)

        results[method] = result

        print()
        print("Method: " + method)
        print("Correct alerts: " + str(result["truePositives"]))
        print("False alerts: " + str(result["falsePositives"]))
        print("Missed events: " + str(result["falseNegatives"]))
        print("Precision: " + str(round(result["precision"], 3)))
        print("Recall: " + str(round(result["recall"], 3)))
        print("F1: " + str(round(result["f1"], 3)))

    return results

def runDemoBenchmark():
    samples = []

    for index in range(80):
        timestampS = round(index * 0.1, 2)

        voltageV = 12.5
        currentA = 40.0

        if timestampS >= 2.0 and timestampS < 2.5:
            voltageV = 6.5

        if timestampS >= 4.0 and timestampS < 4.4:
            currentA = 150.0

        sample = {
            "timestampS": timestampS,
            "voltageV": voltageV,
            "currentA": currentA
        }

        samples.append(sample)

    truthEvents = [
        {
            "signal": "voltageV",
            "startS": 2.0,
            "endS": 2.5
        },
        {
            "signal": "currentA",
            "startS": 4.0,
            "endS": 4.4
        }
    ]

    print("Running an artificial example.")
    return benchmark(samples, truthEvents)