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
        last_sensor_id = -1

        with open(self._filename, "r") as csv_file:
            reader = csv.reader(csv_file)
            for line in reader:
                sensor_id = int(line[0])

                # Scan until we find the first line for sensor 0.
                if scanning and sensor_id != 0:
                    continue
                elif scanning:
                    scanning = False

                if processed_lines >= self._number_of_sensors:
                    # The sweep is complete. Save it and continue with the next one.
                    # In the data matrix, a column contains the RSSI values from a source ID to
                    # all destination IDs. Therefore we want the final column vector to consist
                    # of all columns of the matrix below each other. We select each column,
                    # remove the RSSI value corresponding to the sensor transmitting to itself
                    # (which is not possible) and append the column to the sweep list.
                    data = np.array(lines)
                    sweep = []
                    for index in range(self._number_of_sensors):
                        column = data[:,index].tolist()
                        del column[index]
                        sweep.append(column)
                    sweep = np.array(sweep).reshape(-1, 1)
                    self._sweeps.append(sweep)
                    lines = []
                    processed_lines = 0
                    last_sensor_id = -1

                if processed_lines < self._number_of_sensors:
                    # Ignore sweeps with missing data.
                    if sensor_id != last_sensor_id + 1:
                        scanning = True
                        lines = []
                        processed_lines = 0
                        last_sensor_id = -1
                        continue

                    # Read a line belonging to a sweep. The first number on a line is the ID of
                    # the reporting sensor. The last three numbers represent the timestamp of
                    # the measurement. We skip this data as we do not use it.
                    values = []
                    for index, value in enumerate(line):
                        if index >= 1 and index <= self._number_of_sensors:
                            values.append(int(value))

                    lines.append(values)
                    processed_lines += 1
                    last_sensor_id = sensor_id

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

    def size(self):
        """
        Get the size of the buffer, i.e., the number of sweeps in the file.
        """

        return len(self._sweeps)
