# echonetlite-for-household-solar-power-generation-class

A Python library and toolkit for controlling and testing ECHONET Lite household solar energy generation devices. This project provides utilities for querying, reporting, and comparing ECHONET Lite device properties, with a focus on solar power generation class objects.

## Features
- Query ECHONET Lite devices for property values (EPCs)
- Generate CSV and PDF reports of device status and configuration (with improved reliability and timeout handling)
- Automated physical property testing for settable EPCs (see `physical_tests/new_physical_property_test.py`)
- Compare current device state with default/reference reports
- Automated mapping evaluation and reporting

## Project Structure
```
├── src/                # Main source code (library and utilities)
│   ├── enl_class.py
│   ├── epc_report_query_csv.py
│   ├── epc_report_query_pdf.py
│   ├── EvaluateMapping.py
│   └── exampleUse.py
├── physical_tests/     # Physical and property test scripts
│   ├── new_physical_property_test.py
│   ├── epc_report_comparison.py
│   └── mapping_evaluation_comparison.py
├── tests/              # Unit and comparison scripts
│   ├── test_enl_class_static.py
│   ├── test_epc_report_describe.py
│   ├── test_evaluate_mapping_logic.py
│   └── test_example_use_import.py
├── DefaultReports/     # Reference reports for comparison
├── playground/         # Experimental scripts
├── requirements.txt    # Python dependencies
├── credentials.txt     # Device IP configuration
├── README.md           # Project documentation
```

## Installation
1. Clone the repository or download the project files.
2. Install the required Python packages:

    ```powershell
    pip install -r requirements.txt
    ```

## Configuration
- Set your ECHONET Lite device IP in `credentials.txt`:
  ```
  IP=192.168.1.192
  ```

## Usage
### Query Device and Generate Reports
- To generate a CSV report of device EPCs (with improved timeout handling):
  ```powershell
  python src/epc_report_query_csv.py
  ```
- To generate a PDF report of device EPCs (with improved timeout handling):
  ```powershell
  python src/epc_report_query_pdf.py
  ```
- To run automated physical property tests for settable EPCs and generate a PDF report:
  ```powershell
  python physical_tests/new_physical_property_test.py
  ```
- To evaluate and generate a mapping report:
  ```powershell
  python src/EvaluateMapping.py
  ```

### Compare Reports
- To compare the latest and default EPC CSV reports:
  ```powershell
  python physical_tests/epc_report_comparison.py
  ```
- To compare the latest and default mapping evaluation PDF reports:
  ```powershell
  python physical_tests/mapping_evaluation_comparison.py
  ```

## Notes
- Ensure your device is reachable on the network and the IP is correctly set in `credentials.txt`.
- Default/reference reports for comparison should be placed in the `DefaultReports/` directory in the project root.
- All generated reports (CSV/PDF) will be saved in the project root by default.
- All query and test scripts now use a longer UDP response timeout for improved reliability with ECHONET Lite devices.

## License
See `LICENSE` for license information.
