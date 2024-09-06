import sys
import subprocess
import json
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QPushButton, QLabel, QTextEdit, QWidget

class GPUTestApp(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Button to run the GPU test
        self.runTestButton = QPushButton('Run GPU Test', self)
        self.runTestButton.clicked.connect(self.run_gpu_test)
        layout.addWidget(self.runTestButton)

        # Button to check UUIDs
        self.checkUUIDButton = QPushButton('Check GPU UUIDs', self)
        self.checkUUIDButton.clicked.connect(self.check_gpu_uuids)
        layout.addWidget(self.checkUUIDButton)

        # Text area to display output
        self.outputText = QTextEdit(self)
        layout.addWidget(self.outputText)

        # Label to display the status of GPU
        self.gpuStatusLabel = QLabel('GPU Status: Not Checked', self)
        layout.addWidget(self.gpuStatusLabel)

        # Set layout
        self.setLayout(layout)
        self.setWindowTitle('GPU Test App')
        self.show()

    def run_gpu_test(self):
        # Run the test command
        try:
            result = subprocess.run(['/home/bizon/cuda-samples2/bin/x86_64/linux/release/p2pBandwidthLatencyTest'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output = result.stdout
            self.outputText.setText(output)

            # Analyze the output
            self.analyze_output(output)

        except Exception as e:
            self.outputText.setText(f"Error running the test: {e}")

    def analyze_output(self, output):
        # Extract the Unidirectional P2P=Disabled Bandwidth Matrix
        matrix_found = False
        matrix = []

        for line in output.splitlines():
            if "Unidirectional P2P=Disabled Bandwidth Matrix (GB/s)" in line:
                matrix_found = True
                continue
            if matrix_found:
                if line.strip() == "":  # End of the matrix section
                    break
                # Append only lines that look like bandwidth data
                if any(char.isdigit() for char in line):  # This ensures there are numbers in the line
                    matrix.append(line.strip())

        # Analyze the extracted matrix
        if matrix:
            self.check_bandwidth(matrix)
        else:
            self.gpuStatusLabel.setText("Failed to find Unidirectional P2P matrix in output.")

    def check_bandwidth(self, matrix):
        expected_bandwidth_16x = 22.0  # ~22 GB/s for 16x connected GPUs
        expected_bandwidth_8x = 13.0   # ~13 GB/s for 8x connected GPUs
        expected_on_chip_bandwidth = 900.0  # ~900 GB/s on-chip bandwidth (diagonal)

        issues_found = False
        for i, row in enumerate(matrix):
            try:
                # Remove row and column labels and split the values
                bandwidth_values = [float(val) for val in row.split()[1:]]  # Extract values, ignore first column

                for j, value in enumerate(bandwidth_values):
                    if i == j:
                        # Check diagonal (on-chip bandwidth)
                        if value < expected_on_chip_bandwidth:
                            self.outputText.append(f"Warning: GPU {i} on-chip bandwidth is low: {value} GB/s")
                            issues_found = True
                    else:
                        # Check off-chip bandwidth between GPUs
                        if (i < 3 and j < 3 and value < expected_bandwidth_16x) or (i >= 3 and j >= 3 and value < expected_bandwidth_8x):
                            self.outputText.append(f"Warning: Low bandwidth between GPU {i} and GPU {j}: {value} GB/s")
                            issues_found = True
            except ValueError:
                self.outputText.append(f"Skipping line due to invalid data: {row}")
                continue

        if not issues_found:
            self.gpuStatusLabel.setText("All GPUs are operating within expected bandwidth levels.")
        else:
            self.gpuStatusLabel.setText("Issues detected with GPU bandwidth. Check warnings in output.")

    def check_gpu_uuids(self):
        # Run the nvidia-smi command to get GPU UUIDs
        try:
            result = subprocess.run(['nvidia-smi', '-L'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output = result.stdout

            self.outputText.setText(output)

            # Extract the UUIDs and save them to a file
            uuid_list = []
            for line in output.splitlines():
                if "UUID" in line:
                    gpu_name, uuid = line.split("UUID: ")
                    uuid_list.append({"gpu_name": gpu_name.strip(), "uuid": uuid.strip()})

            # Save the UUIDs to a JSON file
            with open('gpu_uuids.json', 'w') as json_file:
                json.dump(uuid_list, json_file, indent=4)

            self.outputText.append("\nGPU UUIDs saved to gpu_uuids.json")

        except Exception as e:
            self.outputText.setText(f"Error checking UUIDs: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = GPUTestApp()
    sys.exit(app.exec_())
