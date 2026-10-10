import json
from pathlib import Path

from core import readLog, analyzeLog
from benchmark import benchmark, runDemoBenchmark


def main():
    # Choose:
    # "analyze"       - analyze your CSV
    # "demoBenchmark" - test using the artificial example
    # "benchmark"     - score your CSV using its known labels
    mode = "analyze"

    # Choose "fixed" or "adaptive" for analysis.
    method = "fixed"

    # These thresholds apply to fixed detection.
    voltageThreshold = 7.0
    currentThreshold = 110.0

    # Find the folder containing this Python file.
    projectFolder = Path(__file__).resolve().parent

    dataPath = projectFolder / "Data" / "sampleData.csv"
    labelsPath = projectFolder / "Data" / "sampleLabels.json"

    if mode == "analyze":
        analyzeLog(
            dataPath,
            voltageThreshold=voltageThreshold,
            currentThreshold=currentThreshold,
            method=method
        )

    elif mode == "demoBenchmark":
        runDemoBenchmark()

    elif mode == "benchmark":
        samples = readLog(dataPath)

        with open(labelsPath, encoding="utf-8") as file:
            truthEvents = json.load(file)

        benchmark(
            samples,
            truthEvents,
            voltageThreshold=voltageThreshold,
            currentThreshold=currentThreshold
        )

    else:
        raise ValueError("Unknown mode: " + mode)


if __name__ == "__main__":
    main()