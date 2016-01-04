import numpy as np
import csv

class Signal_Strength_File_Reader(object):
    def __init__(self, filename, number_of_sensors):
        """
        Initialize the signal strength file reader object.
        """

        self._filename = filename
        self._number_of_sensors = number_of_sensors

        self._sweeps = []
        self._sweep_id = 0
        self._read()

    def _read(self):
        """
        Read all sweeps from a radio tomographic imaging dataset in CSV format.
        Refer to http://span.ece.utah.edu/rti-data-set for more information.
        """

        scanning = True
        lines = []
        processed_lines = 0

        with open(self._filename, 'r') as csv_file:
            reader = csv.reader(csv_file)
            for line in reader:
                # Scan until we find the first line for node 0.
                if scanning and int(line[0]) != 0:
                    continue
                elif scanning:
                    scanning = False

                if processed_lines >= self._number_of_sensors - 1:
                    # The sweep is complete. Save it and continue with the next one.
                    # In the matrix, a column contains the RSSI values from a source ID to
                    # all destination IDs. Therefore we want the final column vector to consist
                    # of all columns of the matrix below each other. By taking the transpose
                    # of the matrix and reshaping it, we obtain this column vector.
                    sweep = np.array(lines).T.reshape(-1, 1)
                    self._sweeps.append(sweep)
                    lines = []
                    processed_lines = 0

                if processed_lines < self._number_of_sensors - 1:
                    # Read all sweeps in the file.
                    values = []
                    for index, value in enumerate(line):
                        # The first number is the ID of the reporting sensor.
                        # The last three numbers represent the timestamp of the
                        # measurement. We skip this data as we do not use it.
                        if index > 0 and index <= self._number_of_sensors:
                            values.append(int(value))

                    lines.append(values)
                    processed_lines += 1

    def get_sweep(self):
        """
        Get the current sweep and advance the pointer to the next sweep.
        If no more sweeps are left, None is returned.
        """

        if self._sweep_id < len(self._sweeps):
            sweep = self._sweeps[self._sweep_id]
            self._sweep_id += 1
            return sweep

        return None
