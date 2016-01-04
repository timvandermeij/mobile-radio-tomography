import numpy as np
import csv

class Signal_Strength_File_Reader(object):
    def __init__(self, filename, number_of_sensors):
        """
        Initialize the signal strength file reader object.
        """

        self._filename = filename
        self._number_of_sensors = number_of_sensors

    def read(self):
        """
        Read a sweep from a radio tomographic imaging dataset in CSV format.
        Refer to http://span.ece.utah.edu/rti-data-set for more information.
        """

        lines = []
        processed_lines = 0
        reading = False

        with open(self._filename, 'r') as csv_file:
            reader = csv.reader(csv_file)
            for sweep in reader:
                # Scan until we find the first line for node 0.
                if int(sweep[0]) != 0 and not reading:
                    continue

                # Read one entire sweep.
                reading = True
                if processed_lines < self._number_of_sensors - 1:
                    line = []
                    for index, value in enumerate(sweep):
                        # The first number is the ID of the reporting sensor.
                        # The last three numbers represent the timestamp of the
                        # measurement. We skip this data as we do not use it.
                        if index > 0 and index <= self._number_of_sensors:
                            line.append(int(value))

                    lines.append(line)
                    processed_lines += 1
                else:
                    break

        # In the matrix, a column contains the RSSI values from a source ID to
        # all destination IDs. Therefore we want the final column vector to consist
        # of all columns of the matrix below each other. By taking the transpose
        # of the matrix and reshaping it, we obtain this column vector.
        return np.array(lines).T.reshape(-1, 1)
